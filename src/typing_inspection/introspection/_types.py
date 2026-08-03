from types import UnionType
from typing import Any, Protocol

from typing_extensions import TypeVar, TypeAlias, ParamSpec, TypeVarTuple

OriginT = TypeVar('OriginT', default=Any)


class HasParameters(Protocol):
    """An object holding `__parameters__`.

    This can be a [user-defined generic class][user-defined-generics],
    or a [`typing.TypeAliasType`][] instance.
    """
    # Note: `__parameters__` on user-defined generics/TypeAliasType isn't documented,
    # but exposed in `typeshed` and its usage is somewhat widespread already.

    # In theory, this should be `tuple[TypeVarLike, ...]`, but `TypeVarTuple`s get
    # expanded as `typing.Unpack[...]` *only* in type aliases
    # (see https://github.com/python/typeshed/blob/1da0afef/stdlib/typing_extensions.pyi#L622-L624
    # and https://github.com/python/typeshed/pull/13671#discussion_r2003207961):
    __parameters__: tuple[Any, ...]

class GenericAliasLike(Protocol[OriginT]):
    """An instance of a parameterized [generic type][] or typing form.

    Depending on the alias, this may be an instance of [`types.GenericAlias`][]
    (e.g. `list[int]`) or a private `typing` class (`typing._GenericAlias`).
    """
    __origin__: OriginT
    __args__: tuple[Any, ...]
    __parameters__: tuple[Any, ...]


TypeVarLike: TypeAlias = TypeVar | TypeVarTuple | ParamSpec

ParameterizedAnnotationExpr: TypeAlias = GenericAliasLike[Any] | UnionType
