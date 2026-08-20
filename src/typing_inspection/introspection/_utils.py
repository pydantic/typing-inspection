
from typing import Any

from ._types import GenericAliasLike, TypeVarLike, HasParameters, ParameterExpr

from typing_inspection import typing_objects

from typing_extensions import NoDefault, ParamSpec, get_origin

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


def alias_substitutions(alias: GenericAliasLike[HasParameters], /) -> dict[TypeVarLike, Any]:
    origin = alias.__origin__
    params = alias.__origin__.__parameters__
    args = alias.__args__

    # TODO checks for invalid params (most of the checks are already performed
    # by Python for generic classes, but aren't for type aliases)
    ...

    if typing_objects.is_typealiastype(origin) and len(params) == 1 and typing_objects.is_paramspec(params[0]):
        # The end of the documentation section at
        # https://docs.python.org/3/library/typing.html#user-defined-generic-types
        # mentions:
        # > a generic with only one parameter specification variable will accept parameter
        # > lists in the forms X[[Type1, Type2, ...]] and also X[Type1, Type2, ...].
        # Meaning `class A[**P]: ...; get_args(A[int, str]) == get_args(A[[int, str]]) == ((<class 'int'>, <class 'str'>),)`.
        # However, this convenience isn't applied for type aliases.
        if len(args) == 0:
            # Unlike user-defined generics, type aliases don't fallback to the default. This covers
            # the rare case: `type A[**P = [int]] = ...; A[*()].__args__ == ()`. Because we only
            # have one param, the resolved default below can't reference another typevarlike:
            arg = get_default(params[0])
            if typing_objects.is_nodefault(arg):
                raise ValueError
        elif len(args) == 1 and not is_param_expr(args[0]):
            # Apply the convenience mentioned above:
            args = (args,)

    substitutions: dict[TypeVarLike, Any] = {}

    typevartuple_param = next((p for p in params if typing_objects.is_typevartuple(p)), None)

    if typevartuple_param is not None:
        # HARD
        pass
    else:
        return dict(zip(params, args, strict=True))


class A[*Ts, T]:
    a: tuple[int, *Ts]

    def func(self, *args: *Ts): pass



# A[str, *tuple[*()]]

# A[str, *tuple[int, ...]]().a


# A[str, *tuple[int, *tuple[str, ...]]]().a


# Backports of private `typing` functions:

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



def callable_parameter_expr(args: tuple[Any, ...], /) -> ParameterExpr:
    # `__args__` of callable forms is flattened (e.g. `Callable[[int, str], str]` has
    # `__args__` set to `(int, str, str)`), unless the parameter expression is an
    # ellipsis, a `ParamSpec` or a `Concatenate` form. Check adapted from
    # `typing._should_unflatten_callable_args()`:
    # https://github.com/python/cpython/blob/v3.15.0rc1/Lib/typing.py#L215
    if len(args) == 2 and is_param_expr(args[0]):
        return args[0]
    return list(args[:-1])


# Backports of the `__typing_prepare_subst__` methods of type parameter classes,
# only available in 3.11+:

def _paramspec_prepare_subst(self: ParamSpec, alias: GenericAliasLike, args: tuple[Any, ...]):
    params = alias.__parameters__
    i = params.index(self)
    if i == len(args) and not typing_objects.is_nodefault((default := get_default(self))):
        args = (*args, default)
    if i >= len(args):
        raise TypeError(f"Too few arguments for {alias}")
    # Special case where Z[[int, str, bool]] == Z[int, str, bool] in PEP 612.
    if len(params) == 1 and not is_param_expr(args[0]):
        assert i == 0
        args = (args,)
    # Convert lists to tuples to help other libraries cache the results.
    elif isinstance(args[i], list):
        args = (*args[:i], tuple[args[i]], *args[i + 1: ])
    return args
