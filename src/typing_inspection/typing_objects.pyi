# Stub file generated using:
# `stubgen --inspect-mode --include-docstrings -m typing_inspection.typing_objects`
# (manual edits need to be applied).
import sys
from typing import Any, Final, NewType, ParamSpecArgs, ParamSpecKwargs, TypeAliasType, TypeIs, TypeVar

from typing_extensions import ParamSpec, TypeVarTuple

__all__ = [
    'NoneType',
    'is_annotated',
    'is_any',
    'is_classvar',
    'is_concatenate',
    'is_final',
    'is_generic',
    'is_literal',
    'is_literalstring',
    'is_namedtuple',
    'is_never',
    'is_newtype',
    'is_nodefault',
    'is_noreturn',
    'is_notrequired',
    'is_paramspec',
    'is_paramspecargs',
    'is_paramspeckwargs',
    'is_readonly',
    'is_required',
    'is_self',
    'is_typealias',
    'is_typealiastype',
    'is_typeguard',
    'is_typeis',
    'is_typevar',
    'is_typevartuple',
    'is_union',
    'is_unpack',
]

if sys.version_info >= (3, 10):
    from types import NoneType
else:
    NoneType = type(None)

def is_annotated(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.Annotated` :term:`tspec:special form`.

        >>> is_annotated(Annotated)
        True
        >>> is_annotated(Annotated[int, ...])
        False
    """

def is_any(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.Any` :term:`tspec:special form`.

        >>> is_any(Any)
        True
    """

def is_classvar(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.ClassVar` :term:`tspec:type qualifier`.

        >>> is_classvar(ClassVar)
        True
        >>> is_classvar(ClassVar[int])
        >>> False
    """

def is_concatenate(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.Concatenate` :term:`tspec:special form`.

        >>> is_concatenate(Concatenate)
        True
        >>> is_concatenate(Concatenate[int, P])
        False
    """

def is_final(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.Final` :term:`tspec:type qualifier`.

        >>> is_final(Final)
        True
        >>> is_final(Final[int])
        False
    """

def is_generic(obj: Any, /) -> bool:
    """
    Return whether the argument is the :class:`~typing.Generic` :term:`tspec:special form`.

        >>> is_generic(Generic)
        True
        >>> is_generic(Generic[T])
        False
    """

def is_literal(obj: Any, /) -> bool:
    """
    Return whether the argument is the :class:`~typing.Literal` :term:`tspec:special form`.

        >>> is_literal(Literal)
        True
        >>> is_literal(Literal["a"])
        False
    """

def is_paramspec(obj: Any, /) -> TypeIs[ParamSpec]:
    """
    Return whether the argument is an instance of :class:`~typing.ParamSpec`.

        >>> P = ParamSpec('P')
        >>> is_paramspec(P)
        True
    """

def is_typevar(obj: Any, /) -> TypeIs[TypeVar]:
    """
    Return whether the argument is an instance of :class:`~typing.TypeVar`.

        >>> T = TypeVar('T')
        >>> is_typevar(T)
        True
    """

def is_typevartuple(obj: Any, /) -> TypeIs[TypeVarTuple]:
    """
    Return whether the argument is an instance of :class:`~typing.TypeVarTuple`.

        >>> Ts = TypeVarTuple('Ts')
        >>> is_typevartuple(Ts)
        True
    """

def is_union(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.Union` :term:`tspec:special form`.

    This function can also be used to check for the :data:`~typing.Optional` :term:`tspec:special form`,
    as at runtime, :python:`Optional[int]` is equivalent to :python:`Union[int, None]`.

        >>> is_union(Union)
        True
        >>> is_union(Union[int, str])
        False
    """

def is_namedtuple(obj: Any, /) -> bool:
    """Return whether the argument is a named tuple type.

    This includes :class:`typing.NamedTuple` subclasses and classes created from the
    :func:`collections.namedtuple` factory function.

        >>> class User(NamedTuple):
        ...     name: str
        ...
        >>> is_namedtuple(User)
        True
        >>> City = collections.namedtuple('City', [])
        >>> is_namedtuple(City)
        True
        >>> is_namedtuple(NamedTuple)
        False
    """

def is_literalstring(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.LiteralString` :term:`tspec:special form`.

        >>> is_literalstring(LiteralString)
        True
    """

def is_never(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.Never` :term:`tspec:special form`.

        >>> is_never(Never)
        True
    """

def is_newtype(obj: Any, /) -> TypeIs[NewType]:
    """
    Return whether the argument is a :class:`~typing.NewType`.

        >>> UserId = NewType("UserId", int)
        >>> is_newtype(UserId)
        True
    """

def is_nodefault(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.NoDefault` sentinel object.

        >>> is_nodefault(NoDefault)
        True
    """

def is_noreturn(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.NoReturn` :term:`tspec:special form`.

        >>> is_noreturn(NoReturn)
        True
        >>> is_noreturn(Never)
        False
    """

def is_notrequired(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.NotRequired` :term:`tspec:special form`.

        >>> is_notrequired(NotRequired)
        True
    """

def is_paramspecargs(obj: Any, /) -> TypeIs[ParamSpecArgs]:
    """
    Return whether the argument is an instance of :class:`~typing.ParamSpecArgs`.

        >>> P = ParamSpec('P')
        >>> is_paramspecargs(P.args)
        True
    """

def is_paramspeckwargs(obj: Any, /) -> TypeIs[ParamSpecKwargs]:
    """
    Return whether the argument is an instance of :class:`~typing.ParamSpecKwargs`.

        >>> P = ParamSpec('P')
        >>> is_paramspeckwargs(P.kwargs)
        True
    """

def is_readonly(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.ReadOnly` :term:`tspec:special form`.

        >>> is_readonly(ReadOnly)
        True
    """

def is_required(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.Required` :term:`tspec:special form`.

        >>> is_required(Required)
        True
    """

def is_self(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.Self` :term:`tspec:special form`.

        >>> is_self(Self)
        True
    """

def is_typealias(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.TypeAlias` :term:`tspec:special form`.

        >>> is_typealias(TypeAlias)
        True
    """

def is_typeguard(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.TypeGuard` :term:`tspec:special form`.

        >>> is_typeguard(TypeGuard)
        True
    """

def is_typeis(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.TypeIs` :term:`tspec:special form`.

        >>> is_typeis(TypeIs)
        True
    """

def is_typealiastype(obj: Any, /) -> TypeIs[TypeAliasType]:
    """
    Return whether the argument is a :class:`~typing.TypeAliasType` instance.

        >>> type MyInt = int
        >>> is_typealiastype(MyInt)
        True
        >>> MyStr = TypeAliasType("MyStr", str)
        >>> is_typealiastype(MyStr):
        True
        >>> type MyList[T] = list[T]
        >>> is_typealiastype(MyList[int])
        False
    """

def is_unpack(obj: Any, /) -> bool:
    """
    Return whether the argument is the :data:`~typing.Unpack` :term:`tspec:special form`.

        >>> is_unpack(Unpack)
        True
        >>> is_unpack(Unpack[Ts])
        False
    """

DEPRECATED_ALIASES: Final[dict[Any, type[Any]]]
"""A mapping between the deprecated typing aliases to their replacement, as per :pep:`585`."""
