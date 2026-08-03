import types
import sys
import functools
import operator
import collections.abc
from typing import Any, ForwardRef, Literal, Union, cast

from typing_extensions import Unpack, TypeForm, get_origin

from ._types import ParameterizedAnnotationExpr
from ._utils import _is_param_expr
from typing_inspection import typing_objects



class TypeHintVisitorException(Exception):
    pass


class InvalidExpression(TypeHintVisitorException):
    """The expression isn't valid."""

    invalid_expression: Any
    """The encountered invalid expression."""

    def __init__(self, invalid_expression: Any) -> None:
        self.invalid_expression = invalid_expression

class UnevaluatedTypeHint(TypeHintVisitorException):
    """The type hint wasn't evaluated as it still contains forward references."""

    forward_arg: ForwardRef | str
    """The forward reference that wasn't evaluated."""

    def __init__(self, forward_arg: ForwardRef | str) -> None:
        self.forward_arg = forward_arg


class TypeHintVisitor:
    def visit(self, annotation_expr: TypeForm[Any]) -> None:
        origin = get_origin(annotation_expr)
        if origin is not None:
            if typing_objects.is_generic(origin):
                # `get_origin()` returns `Generic` if `annotation_expr` is `typing.Generic` (or `Generic[...]`).
                raise InvalidExpression(annotation_expr)

            if (
                # For *bare* deprecated aliases (such as `typing.List`), `get_origin()` returns the
                # actual type (such as `list`). As such, we treat `annotation_expr` as a bare hint.
                annotation_expr in typing_objects.DEPRECATED_ALIASES
                # For `ParamSpecArgs`/`ParamSpecKwargs`, `get_origin()` returns the `ParamSpec` instance.
                # As such, treat the `ParamSpecArgs`/`ParamSpecKwargs` as a bare annotation_expr.
                or typing_objects.is_paramspec(origin)
            ):
                return self.visit_bare_annotation_expr(annotation_expr)

            # Otherwise, `annotation_expr` is a generic alias or a `UnionType`. We call these two "parameterized annotation expressions":
            parameterized_ann_expr = cast(ParameterizedAnnotationExpr, annotation_expr)
            return self.visit_parameterized_annotation_expr(parameterized_ann_expr, origin)
        else:
            return self.visit_bare_annotation_expr(annotation_expr)


    def visit_parameterized_annotation_expr(self, annotation_expr: ParameterizedAnnotationExpr, origin: Any) -> None:
        if not typing_objects.is_literal(origin):
            # Note: it is important to use `hint.__args__` instead of `get_args()` as
            # they differ for some typing forms (e.g. `Annotated`, `Callable`).
            # `hint.__args__` should be guaranteed to only contain other annotation expressions.
            for arg in annotation_expr.__args__:
                self.visit(arg)

    def visit_bare_annotation_expr(self, annotation_expr: Any) -> None:
        if typing_objects.is_forwardref(annotation_expr) or isinstance(annotation_expr, str):
            self.visit_forward_expr(annotation_expr)

    def visit_forward_expr(self, forward_expr: ForwardRef | str) -> None:
        raise UnevaluatedTypeHint(forward_expr)


# Backport of `typing._should_unflatten_callable_args()`:
def _should_unflatten_callable_args(alias: types.GenericAlias, args: tuple[Any, ...]) -> bool:
    return (
        alias.__origin__ is collections.abc.Callable  # pyright: ignore
        and not (len(args) == 2 and _is_param_expr(args[0]))
    )


class TypeHintTransformer:

    def visit(self, annotation_expr: TypeForm[Any]) -> Any:
        origin = get_origin(annotation_expr)
        if origin is not None:
            if typing_objects.is_generic(origin):
                # `get_origin()` returns `Generic` if `annotation_expr` is `typing.Generic` (or `Generic[...]`).
                raise InvalidExpression(annotation_expr)

            if (
                # For *bare* deprecated aliases (such as `typing.List`), `get_origin()` returns the
                # actual type (such as `list`). As such, we treat `annotation_expr` as a bare hint.
                annotation_expr in typing_objects.DEPRECATED_ALIASES
                # For `ParamSpecArgs`/`ParamSpecKwargs`, `get_origin()` returns the `ParamSpec` instance.
                # As such, treat the `ParamSpecArgs`/`ParamSpecKwargs` as a bare annotation_expr.
                or typing_objects.is_paramspec(origin)
            ):
                return self.visit_bare_annotation_expr(annotation_expr)

            # Otherwise, `annotation_expr` is a generic alias or a `UnionType`. We call these two "parameterized annotation expressions":
            parameterized_ann_expr = cast(ParameterizedAnnotationExpr, annotation_expr)
            return self.visit_parameterized_annotation_expr(parameterized_ann_expr, origin)
        else:
            return self.visit_bare_annotation_expr(annotation_expr)

    def visit_parameterized_annotation_expr(self, annotation_expr: ParameterizedAnnotationExpr, origin: Any) -> Any:
        if typing_objects.is_literal(origin):
            return annotation_expr

        visited_args = tuple(self.visit(arg) for arg in annotation_expr.__args__)
        if visited_args == annotation_expr.__args__:
            return annotation_expr

        if origin is types.UnionType:
            if sys.version_info >= (3, 14):
                # In Python >= 3.14, types.UnionType and typing.Union are the same types. If any of
                # the `visited_args` are strings (e.g. `('Forward', int)`), using `functools.reduce()`
                # with `or_` fails with a `TypeError` (Encountering forward refs results in a
                # `UnevaluatedTypeHint` by default, but users can override this by implementing
                # `visit_forward_expr()`).
                return Union[visited_args]
            return functools.reduce(operator.or_, visited_args)
        elif isinstance(annotation_expr, types.GenericAlias):
            # Logic from `typing._eval_type()`:
            if sys.version_info >= (3, 11):
                is_unpacked = annotation_expr.__unpacked__
            else:
                is_unpacked = False
            if _should_unflatten_callable_args(annotation_expr, visited_args):
                t = annotation_expr.__origin__[(visited_args[:-1], visited_args[-1])]
            else:
                t = annotation_expr.__origin__[visited_args]
            if is_unpacked:
                t = Unpack[t]
            return t
        else:
            # `.copy_with()` is a method present on the private `typing._GenericAlias` class.
            # Many generic aliases (e.g. `Concatenate[]`) have special logic in this method,
            # so we can't just do `hint.__origin__[transformed_args]`.
            return annotation_expr.copy_with(visited_args)  # pyright: ignore

    def visit_bare_annotation_expr(self, annotation_expr: Any) -> Any:
        if typing_objects.is_forwardref(annotation_expr) or isinstance(annotation_expr, str):
            return self.visit_forward_expr(annotation_expr)
        else:
            return annotation_expr

    def visit_forward_expr(self, forward_expr: ForwardRef | str) -> Any:
        raise UnevaluatedTypeHint(forward_expr)


class MultiTransformer(TypeHintTransformer):
    def __init__(
        self,
        unpack_type_aliases: Literal['skip', 'lenient', 'eager'] = 'skip',
        type_replacements: dict[Any, Any] = {},
    ) -> None:
        self.unpack_type_aliases: Literal['skip', 'lenient', 'eager'] = unpack_type_aliases
        self.type_replacements = type_replacements

    def visit_parameterized_annotation_expr(self, annotation_expr: ParameterizedAnnotationExpr, origin: Any) -> TypeForm[Any]:
        args = annotation_expr.__args__
        if self.unpack_type_aliases != 'skip' and typing_objects.is_typealiastype(origin):
            try:
                value = origin.__value__
            except NameError:
                if self.unpack_type_aliases == 'eager':
                    raise
            else:
                return self.visit(value[tuple(self.visit(arg) for arg in args)])
        return super().visit_parameterized_annotation_expr(annotation_expr, origin)


    def visit_bare_annotation_expr(self, annotation_expr: Any) -> Any:
        annotation_expr = super().visit_bare_annotation_expr(annotation_expr)
        new_annotation_expr = self.type_replacements.get(annotation_expr, annotation_expr)
        if self.unpack_type_aliases != 'skip' and typing_objects.is_typealiastype(new_annotation_expr):
            try:
                value = new_annotation_expr.__value__
            except NameError:
                if self.unpack_type_aliases == 'eager':
                    raise
            else:
                return self.visit(value)
        return new_annotation_expr


def transform_hint(
    hint: Any,
    unpack_type_aliases: Literal['skip', 'lenient', 'eager'] = 'skip',
    type_replacements: dict[Any, Any] = {},
) -> Any:
    ...
