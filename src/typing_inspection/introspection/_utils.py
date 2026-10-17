
import sys
from types import SimpleNamespace
from typing import Any, cast

from ._types import GenericAliasLike, TypeVarLike, HasParameters, ParameterExpr

from typing_inspection import typing_objects

from typing_extensions import NoDefault, ParamSpec, TypeAliasType, get_origin

def get_default(t: TypeVarLike, /) -> Any:
    """Get the default value of a type parameter, if it exists.

    Args:
        t: The [`TypeVar`][typing.TypeVar], [`TypeVarTuple`][typing.TypeVarTuple] or
            [`ParamSpec`][typing.ParamSpec] instance to get the default from.

    Returns:
        The default value, or [`typing.NoDefault`] if not default is set.
            !!! warning
                This function may return the [`NoDefault` backport][typing_extensions.NoDefault] backport
                from `typing_extensions`. As such, [`typing_objects.is_nodefault()`][typing_inspection.typing_objects.is_nodefault]
                should be used.
    """

    try:
        has_default = t.has_default()
    except AttributeError:
        return NoDefault
    else:
        if has_default:
            return t.__default__
        else:
            return NoDefault


def alias_substitutions(
    alias: GenericAliasLike[HasParameters | TypeAliasType], /, *, resolve_default_references: bool = False
) -> dict[TypeVarLike, Any]:
    """Map the type parameters of the alias' origin to the alias' arguments.

    In the general case, the alias is assumed to be valid. Otherwise, a [`ValueError`] is raised if arguments
    can't be matched against parameters.

    Args:
        alias: The parameterized alias to extract the substitutions from. The alias can be for a generic class
        or a [`typing.TypeAliasType`][] instance.
        resolve_default_references: Whether to substitute type parameters appearing in the
            default value of a later type parameter:

              ```pycon
              >>> type A[T1 = int, T2 = list[T1]] = tuple[T1, T2]
              >>> alias_substitutions(A[str], resolve_default_references=True)
              {T1: <class 'str'>, T2: list[str]}
              >>> alias_substitutions(A[str], resolve_default_references=False)  # The default
              {T1: <class 'str'>, T2: list[T1]}
              ```

            Note that an explicit argument equal to the default (e.g. `A[str, list[T1]]`) can't be told apart
            from the default at runtime, and is treated as if the default was used:

    Returns:
        A mapping of each type parameter to its argument, in declaration order.
            [`TypeVarTuple`][typing.TypeVarTuple] parameters are mapped to the tuple of the packed
            arguments, and [`ParamSpec`][typing.ParamSpec] parameters to a tuple of the parameter
            expression's types (or an ellipsis, a `ParamSpec` or a `Concatenate` form).

    Example:
        ```pycon
        >>> class A[**P]: ...
        >>> type B[**P] = A[P]
        >>> alias_substitutions(A[int, str]) == alias_substitutions(B[int, str]) == {P: (int, str)}
        ```
    """
    origin = alias.__origin__
    args = alias.__args__

    params: tuple[TypeVarLike, ...]
    mapping: dict[TypeVarLike, Any]
    if typing_objects.is_typealiastype(origin):
        # Unlike generic classes, no processing of the argument of type aliases are performed
        # (see https://github.com/python/cpython/issues/132100).
        # For generic classes, this processing roughly iterates over the parameters of the class and
        # computes new args by doing `args = parameter.__typing_prepare_subst__(cls, args)`.
        # (see `typing._generic_class_getitem()` in https://github.com/python/cpython/blob/v3.15.0rc1/Lib/typing.py#L1158).
        #
        # This `__typing_prepare_subst__()` method handles falling back to the default, doing processing
        # on args, etc. It was introduced in 3.11, so we can't unconditionally use it as we still support 3.10
        # Fortunately, we only need to vendor the `ParamSpec.__typing_prepare_subst__()` implementation as:
        # - `typing.TypeVarTuple` only exists in 3.11, and using `typing_extensions.TypeVarTuple` on 3.10 is
        #   fine as it also has a backported `__typing_prepare_subst__()` implementation.
        # - `typing.TypeVar`'s `__typing_prepare_subst__()` only has logic to fall back to its default if no
        #   arg is provided. On 3.10, `typing.TypeVar` can't have a default, and `typing_extensions.TypeVar`
        #   also has a backported `__typing_prepare_subst__()` implementation.
        #
        # Sources:
        # `typing.TypeVar`: https://github.com/python/cpython/blob/v3.15.0rc1/Objects/typevarobject.c#L779
        # `typing.ParamSpec`: https://github.com/python/cpython/blob/v3.15.0rc1/Lib/typing.py#L1140
        # `typing.TypeVarTuple`: https://github.com/python/cpython/blob/v3.15.0rc1/Lib/typing.py#L1090
        #
        # Relying on the stdlib/`typing_extensions` (complex) implementation saves us from vendoring them, however
        # we need to apply a small trick to make it work:
        # Unlike generic classes, `__parameters__` wrap `TypeVarTuple`s in `Unpack[...]` *only* for type aliases:
        # `type A[*Ts] = ...; A.__parameters__ == (Unpack[Ts],)`.
        # `__type_params__` stores the type parameters as declared, so we use that:
        params = origin.__type_params__

        # This is problematic because the `__typing_prepare_subst__()` are meant for classes, and so they use
        # `__parameters__` and not `__type_params__` (as it doesn't work with old style classes, e.g. `class A(Generic[T]): ...`).
        # We define a duck-typed `subst_alias` to "lie" to `__typing_prepare_subst__()`:
        subst_alias = SimpleNamespace(__parameters__=params)

        args = tuple(_unpack_args(*args))
        for param in params:
            prepare = getattr(param, '__typing_prepare_subst__', None)
            if prepare is not None:
                try:
                    args = tuple(prepare(subst_alias, args))
                except TypeError:
                    raise ValueError from None
            elif sys.version_info < (3, 11) and typing_objects.is_paramspec(param):
                # As per comment above:
                args = _paramspec_prepare_subst(param, params, args)
        if len(args) != len(params):
            raise ValueError
        mapping = dict(zip(params, args))
    else:
        params = origin.__parameters__
        # For generic classes, the runtime already performed the processing above at
        # parameterization time, but re-flattened the packed `TypeVarTuple` arguments
        # into `__args__`. We only need to unflatten:
        tvt_index = next((i for i, p in enumerate(params) if typing_objects.is_typevartuple(p)), None)
        if tvt_index is None:
            if len(args) != len(params):
                raise ValueError
            mapping = dict(zip(params, args))
        else:
            right = len(params) - tvt_index - 1
            if len(args) < len(params) - 1:
                raise ValueError
            mapping = dict(zip(params[:tvt_index], args))
            mapping[params[tvt_index]] = tuple(args[tvt_index : len(args) - right])
            mapping.update(zip(params[tvt_index + 1 :], args[len(args) - right :]))

    # Arguments may be stored as lists (e.g. `ParamSpec` parameter expressions, or a packed
    # `TypeVarTuple` default expanded by the runtime); normalize them to tuples:
    mapping = {p: tuple(cast('list[Any]', v)) if isinstance(v, list) else v for p, v in mapping.items()}

    if not resolve_default_references:
        return mapping

    # Type parameters appearing in the default value of a later type parameter are not substituted
    # (e.g. with `class A[T1 = int, T2 = list[T1]]: ...`, `A[str].__args__` is `(str, list[T1])`).
    # As per PEP 696, `T2` should resolve to `list[str]`, so whenever an argument comes from a default value, apply
    # the substitutions known so far. Note that an explicit argument equal to the default (e.g. `A[str, list[T1]]`)
    # can't be told apart from the default at runtime, and is treated as if the default was used:
    substitutions: dict[TypeVarLike, Any] = {}
    for param, value in mapping.items():
        if substitutions and _is_default_value(param, value):
            value = _apply_substitutions(value, substitutions)
            if typing_objects.is_paramspec(param) and isinstance(value, list):
                value = tuple(cast('list[Any]', value))
        substitutions[param] = value
    return substitutions


def _is_default_value(param: TypeVarLike, value: Any, /) -> bool:
    """Whether `value` is (or is indistinguishable from) the default value of `param`."""
    default = get_default(param)
    if typing_objects.is_nodefault(default):
        return False
    if typing_objects.is_typevartuple(param):
        return value == tuple(_unpack_args(default))
    if typing_objects.is_paramspec(param) and isinstance(default, list):
        return value == tuple(cast('list[Any]', default))
    return value is default or value == default


def _apply_substitutions(value: Any, substitutions: 'dict[TypeVarLike, Any]', /) -> Any:
    """Substitute the type parameters appearing in `value` (a default value of a later type parameter)."""
    from ._parsing import MultiTransformer

    replacements: dict[Any, Any] = {}
    for param, sub in substitutions.items():
        if typing_objects.is_typevartuple(param):
            # A default value can't reference a `TypeVarTuple`, as type parameters
            # with a default can't follow a `TypeVarTuple` (per PEP 696):
            continue
        if typing_objects.is_paramspec(param) and isinstance(sub, tuple):
            # Use the list form, understood by the transformer as a parameter expression:
            sub = list(cast('tuple[Any, ...]', sub))
        replacements[param] = sub
    transformer = MultiTransformer(type_replacements=replacements)
    if isinstance(value, tuple):
        # A packed `TypeVarTuple` or `ParamSpec` argument:
        return tuple(transformer.visit(v) for v in cast('tuple[Any, ...]', value))
    return transformer.visit(value)


# Vendored versions of private `typing` functions:

# Vendored version of `typing._is_param_expr()`, adapted to be compatible
# with both `typing`and `typing_extensions`, and without relying on private constructs.
# Source: https://github.com/python/cpython/blob/v3.15.0rc1/Lib/typing.py#L210
def is_param_expr(arg: Any) -> bool:
    return (
        arg is ...  # as in `Callable[..., Any]`
        or isinstance(arg, (tuple, list))  # as in `Callable[[int, str], Any]`
        or typing_objects.is_paramspec(arg)  # as in `Callable[P, Any]`
        or typing_objects.is_concatenate(get_origin(arg))  # as in `Callable[Concatenate[int, P], Any]`
    )


# Adapted from `typing._should_unflatten_callable_args()`. See its docstring for more details.
# Source: https://github.com/python/cpython/blob/v3.15.0rc1/Lib/typing.py#L215.
def callable_parameter_expr(args: tuple[Any, ...], /) -> ParameterExpr:
    if len(args) == 2 and is_param_expr(args[0]):
        return args[0]
    return list(args[:-1])


# Vendored version of `typing._unpack_args()`, flattening unpacked fixed-length
# tuples (e.g. `*tuple[int, str]` is expanded to `int, str`).
# Source: https://github.com/python/cpython/blob/v3.15.0rc1/Lib/typing.py#L356
def _unpack_args(*args: Any) -> list[Any]:
    newargs: list[Any] = []
    for arg in args:
        subargs = getattr(arg, '__typing_unpacked_tuple_args__', None)
        if subargs is not None and not (subargs and subargs[-1] is ...):
            newargs.extend(subargs)
        else:
            newargs.append(arg)
    return newargs


if sys.version_info < (3, 11):
    # `__typing_prepare_subst__()` was introduced in 3.11, so on 3.10 the substitution processing
    # of `typing.ParamSpec` instances needs to be backported.
    # Adapted from `typing._paramspec_prepare_subst()`:
    # https://github.com/python/cpython/blob/v3.15.0rc1/Lib/typing.py#L1140
    # Adaptations: the type parameters are taken directly (instead of being fetched from the
    # alias), the default is fetched with `get_default()`, and bare `ValueError`s are raised.
    def _paramspec_prepare_subst(self: ParamSpec, params: 'tuple[TypeVarLike, ...]', args: 'tuple[Any, ...]') -> 'tuple[Any, ...]':
        i = params.index(self)
        if i == len(args) and not typing_objects.is_nodefault(default := get_default(self)):
            args = (*args, default)
        if i >= len(args):
            # Too few arguments:
            raise ValueError
        # Special case where Z[[int, str, bool]] == Z[int, str, bool] in PEP 612.
        if len(params) == 1 and not is_param_expr(args[0]):
            assert i == 0
            args = (args,)
        # Convert lists to tuples to help other libraries cache the results.
        elif isinstance(args[i], list):
            args = (*args[:i], tuple(args[i]), *args[i+1:])
        return args
