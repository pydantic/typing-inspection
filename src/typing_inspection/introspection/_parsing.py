import types
import sys
import functools
import operator
import collections.abc
from typing import Any, ForwardRef, Literal

from typing_extensions import Unpack, get_origin

from ._types import GenericAliasProto
from ._utils import _is_param_expr
from typing_inspection import typing_objects



class UnevaluatedTypeHint(Exception):
    """The type hint wasn't evaluated as it still contains forward references."""

    forward_arg: ForwardRef | str
    """The forward reference that wasn't evaluated."""

    def __init__(self, forward_arg: ForwardRef | str) -> None:
        self.forward_arg = forward_arg

class TypeHintVisitor:

    def visit(self, hint: Any) -> None:
        if typing_objects.is_paramspecargs(hint) or typing_objects.is_paramspeckwargs(hint):
            return self.visit_bare_hint(hint)
        origin = get_origin(hint)
        if typing_objects.is_generic(origin):
            # `get_origin()` returns `Generic` if `hint` is `typing.Generic` (or `Generic[...]`).
            raise ValueError(f'{hint} is invalid in an annotation expression')

        if origin is not None:
            if hint in typing_objects.DEPRECATED_ALIASES:
                # For *bare* deprecated aliases (such as `typing.List`), `get_origin()` returns the
                # actual type (such as `list`). As such, we treat `hint` as a bare hint.
                self.visit_bare_hint(hint)
            elif sys.version_info >= (3, 10) and origin is types.UnionType:
                self.visit_union(hint)
            else:
                self.visit_generic_alias(hint, origin)
        else:
            self.visit_bare_hint(hint)

        # origin = get_origin(hint)
        # if origin in DEPRECATED_ALIASES.values() and not isinstance(hint, types.GenericAlias):
        #     # hint is a deprecated generic alias, e.g. `List[int]`.
        #     # `get_origin(List[int])` returns `list`, but we want to preserve
        #     # `List` as the actual origin.

    def visit_generic_alias(self, hint: GenericAliasProto, origin: Any) -> None:
        if not typing_objects.is_literal(origin):
            # Note: it is important to use `hint.__args__` instead of `get_args()` as
            # they differ for some typing forms (e.g. `Annotated`, `Callable`).
            # `hint.__args__` should be guaranteed to only contain other annotation expressions.
            for arg in hint.__args__:
                self.visit(arg)

    if sys.version_info >= (3, 10):
        def visit_union(self, hint: types.UnionType) -> None:
            for arg in hint.__args__:
                self.visit(arg)

    def visit_bare_hint(self, hint: Any) -> None:
        if typing_objects.is_forwardref(hint) or isinstance(hint, str):
            self.visit_forward_hint(hint)

    def visit_forward_hint(self, hint: ForwardRef | str) -> None:
        raise UnevaluatedTypeHint(hint)


# Backport of `typing._should_unflatten_callable_args`:
def _should_unflatten_callable_args(alias: types.GenericAlias, args: tuple[Any, ...]) -> bool:
    return (
        alias.__origin__ is collections.abc.Callable  # pyright: ignore
        and not (len(args) == 2 and _is_param_expr(args[0]))
    )


class TypeHintTransformer:

    def visit(self, hint: Any) -> Any:
        if typing_objects.is_paramspecargs(hint) or typing_objects.is_paramspeckwargs(hint):
            return self.visit_bare_hint(hint)
        origin = get_origin(hint)
        if typing_objects.is_generic(origin):
            # `get_origin()` returns `Generic` if `hint` is `typing.Generic` (or `Generic[...]).
            raise ValueError(f'{hint} is invalid in an annotation expression')

        if origin is not None:
            if hint in typing_objects.DEPRECATED_ALIASES:
                # For *bare* deprecated aliases (such as `typing.List`), `get_origin()` returns the
                # actual type (such as `list`). As such, we treat `hint` as a constant.
                return self.visit_bare_hint(hint)
            elif sys.version_info >= (3, 10) and origin is types.UnionType:
                return self.visit_union(hint)
            else:
                return self.visit_generic_alias(hint, origin)
        else:
            return self.visit_bare_hint(hint)

    def visit_generic_alias(self, hint: GenericAliasProto, origin: Any) -> Any:
        if typing_objects.is_literal(origin):
            return hint

        visited_args = tuple(self.visit(arg) for arg in hint.__args__)
        if visited_args == hint.__args__:
            return hint

        if isinstance(hint, types.GenericAlias):
            # Logic from `typing._eval_type()`:
            is_unpacked = hint.__unpacked__
            if _should_unflatten_callable_args(hint, visited_args):
                t = hint.__origin__[(visited_args[:-1], visited_args[-1])]
            else:
                t = hint.__origin__[visited_args]
            if is_unpacked:
                t = Unpack[t]
            return t
        else:
            # `.copy_with()` is a method present on the private `typing._GenericAlias` class.
            # Many generic aliases (e.g. `Concatenate[]`) have special logic in this method,
            # so we can't just do `hint.__origin__[transformed_args]`.
            return hint.copy_with(visited_args)  # pyright: ignore

    if sys.version_info >= (3, 10):
        def visit_union(self, hint: types.UnionType) -> Any:
            visited_args = tuple(self.visit(arg) for arg in hint.__args__)
            if visited_args == hint.__args__:
                return hint
            return functools.reduce(operator.or_, visited_args)

    def visit_bare_hint(self, hint: Any) -> Any:
        if typing_objects.is_forwardref(hint) or isinstance(hint, str):
            return self.visit_forward_hint(hint)
        else:
            return hint

    def visit_forward_hint(self, hint: ForwardRef | str) -> Any:
        raise UnevaluatedTypeHint(hint)


class MultiTransformer(TypeHintTransformer):
    def __init__(
        self,
        unpack_type_aliases: Literal['skip', 'lenient', 'eager'] = 'skip',
        type_replacements: dict[Any, Any] = {},
    ) -> None:
        self.unpack_type_aliases: Literal['skip', 'lenient', 'eager'] = unpack_type_aliases
        self.type_replacements = type_replacements

    def visit_generic_alias(self, hint: GenericAliasProto, origin: Any) -> Any:
        args = hint.__args__
        if self.unpack_type_aliases != 'skip' and typing_objects.is_typealiastype(origin):
            try:
                value = origin.__value__
            except NameError:
                if self.unpack_type_aliases == 'eager':
                    raise
            else:
                return self.visit(value[tuple(self.visit(arg) for arg in args)])
        return super().visit_generic_alias(hint, origin)


    def visit_bare_hint(self, hint: Any) -> Any:
        hint = super().visit_bare_hint(hint)
        new_hint = self.type_replacements.get(hint, hint)
        if self.unpack_type_aliases != 'skip' and typing_objects.is_typealiastype(new_hint):
            try:
                value = new_hint.__value__
            except NameError:
                if self.unpack_type_aliases == 'eager':
                    raise
            else:
                return self.visit(value)
        return new_hint


def transform_hint(
    hint: Any,
    unpack_type_aliases: Literal['skip', 'lenient', 'eager'] = 'skip',
    type_replacements: dict[Any, Any] = {},
) -> Any:
    ...
