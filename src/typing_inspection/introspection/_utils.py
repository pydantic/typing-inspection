import sys

from typing import Any

from ._types import GenericAliasProto, TypeVarLike

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


def alias_substitutions(alias: GenericAliasProto, /) -> dict[TypeVarLike, Any]:
    params: tuple[TypeVarLike, ...] | None = getattr(alias.__origin__, '__parameters__', None)
    if params is None:
        raise ValueError

    origin = alias.__origin__
    args = alias.__args__

    # TODO checks for invalid params (most of the checks are already performed
    # by Python for generic classes, but aren't for type aliases)
    ...

    if typing_objects.is_typealiastype(origin) and len(params) == 1 and typing_objects.is_paramspec(params[0]):
        # The end of the documentation section at
        # https://docs.python.org/3/library/typing.html#user-defined-generic-types
        # says:
        # a generic with only one parameter specification variable will accept parameter
        # lists in the forms X[[Type1, Type2, ...]] and also X[Type1, Type2, ...].
        # However, this convenience isn't applied for type aliases.
        if len(args) == 0:
            # Unlike user-defined generics, type aliases don't fallback to the default:
            arg = get_default(params[0])
            if typing_objects.is_nodefault(arg):
                raise ValueError
        elif len(args) == 1 and not _is_param_expr(args[0]):
            arg = args[0]

        if not _is_param_expr(arg):
            arg = (arg,)
        elif isinstance(arg, list):
            arg = tuple(arg)

    substitutions: dict[TypeVarLike, Any] = {}

    typevartuple_param = next((p for p in params if typing_objects.is_typevartuple(p)), None)

    if typevartuple_param is not None:
        # HARD
        pass
    else:
        strict = {'strict': True} if sys.version_info >= (3, 10) else {}
        return dict(zip(params, args), **strict)


class A[*Ts, T]:
    a: tuple[int, *Ts]

    def func(self, *args: *Ts): pass



A[str, *tuple[*()]]

A[str, *tuple[int, ...]]().a


A[str, *tuple[int, *tuple[str, ...]]]().a


# Backports of private `typing` functions:

# Backport of `typing._is_param_expr`:
def _is_param_expr(arg: Any) -> bool:
    return (
        arg is ...  # as in `Callable[..., Any]`
        or isinstance(arg, (tuple, list))  # as in `Callable[[int, str], Any]`
        or typing_objects.is_paramspec(arg)  # as in `Callable[P, Any]`
        or typing_objects.is_concatenate(get_origin(arg))  # as in `Callable[Concatenate[int, P], Any]`
    )

# Backports of the `__typing_prepare_subst__` methods of type parameter classes,
# only available in 3.11+:

def _paramspec_prepare_subst(self: ParamSpec, alias: GenericAliasProto, args: tuple[Any, ...]):
    params = alias.__parameters__
    i = params.index(self)
    if i == len(args) and not typing_objects.is_nodefault((default := get_default(self))):
        args = (*args, default)
    if i >= len(args):
        raise TypeError(f"Too few arguments for {alias}")
    # Special case where Z[[int, str, bool]] == Z[int, str, bool] in PEP 612.
    if len(params) == 1 and not _is_param_expr(args[0]):
        assert i == 0
        args = (args,)
    # Convert lists to tuples to help other libraries cache the results.
    elif isinstance(args[i], list):
        args = (*args[:i], tuple[args[i]], *args[i + 1: ])
    return args
