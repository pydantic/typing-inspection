from typing import Any, Protocol

from typing_extensions import TypeVar, TypeAlias, ParamSpec, TypeVarTuple

OriginT = TypeVar('OriginT', default=Any)

class GenericAliasProto(Protocol[OriginT]):
    """An instance of a parameterized [generic type][] or typing form.

    Depending on the alias, this may be an instance of [`types.GenericAlias`][]
    (e.g. `list[int]`) or a private `typing` class (`typing._GenericAlias`).
    """
    __origin__: OriginT
    __args__: tuple[Any, ...]
    __parameters__: tuple[Any, ...]


TypeVarLike: TypeAlias = 'TypeVar | TypeVarTuple | ParamSpec'
