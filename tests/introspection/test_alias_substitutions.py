import sys
import typing
from textwrap import dedent
from typing import Any, Callable, Generic

import pytest
from typing_extensions import ParamSpec, TypeAliasType, TypeVar, TypeVarTuple, Unpack

from typing_inspection.introspection._utils import alias_substitutions

T = TypeVar('T')
T1 = TypeVar('T1')
T2 = TypeVar('T2')
Ts = TypeVarTuple('Ts')
P = ParamSpec('P')


def test_class() -> None:
    class A(Generic[T]): ...

    assert alias_substitutions(A[int]) == {T: int}


def test_class_paramspec_convenience() -> None:
    class A(Generic[P]): ...

    assert alias_substitutions(A[int, str]) == {P: (int, str)}
    assert alias_substitutions(A[[int, str]]) == {P: (int, str)}


def test_class_typevartuple() -> None:
    class A(Generic[T, Unpack[Ts]]): ...

    assert alias_substitutions(A[int, str, bytes]) == {T: int, Ts: (str, bytes)}
    assert alias_substitutions(A[int]) == {T: int, Ts: ()}


def test_class_chained_alias() -> None:
    class A(Generic[T1, T2]): ...

    # Subscripting an alias goes through the runtime's substitution machinery,
    # and `__origin__` still points to `A`:
    assert alias_substitutions(A[int, list[T2]][str]) == {T1: int, T2: list[str]}


def test_type_alias() -> None:
    A = TypeAliasType('A', list[T], type_params=(T,))

    assert alias_substitutions(A[int]) == {T: int}


def test_type_alias_paramspec_convenience() -> None:
    A = TypeAliasType('A', Callable[P, int], type_params=(P,))

    assert alias_substitutions(A[int, str]) == {P: (int, str)}
    assert alias_substitutions(A[[int, str]]) == {P: (int, str)}
    assert alias_substitutions(A[...]) == {P: ...}
    assert alias_substitutions(A[P]) == {P: P}


def test_type_alias_stdlib_paramspec() -> None:
    # On 3.10, stdlib `ParamSpec` instances don't implement `__typing_prepare_subst__`,
    # exercising the vendored `_paramspec_prepare_subst()` backport:
    P_std = typing.ParamSpec('P_std')
    A = TypeAliasType('A', Callable[P_std, int], type_params=(P_std,))

    assert alias_substitutions(A[int, str]) == {P_std: (int, str)}
    assert alias_substitutions(A[[int, str]]) == {P_std: (int, str)}


def test_type_alias_typevar_defaults() -> None:
    T1_d = TypeVar('T1_d', default=int)
    T2_d = TypeVar('T2_d', default=list[T1_d])
    A = TypeAliasType('A', tuple[T1_d, T2_d], type_params=(T1_d, T2_d))

    # By default, type parameters referenced in the default value of `T2_d` are left as is:
    assert alias_substitutions(A[str]) == {T1_d: str, T2_d: list[T1_d]}
    # With `resolve_default_references`, they are resolved with the substitutions known so far:
    assert alias_substitutions(A[str], resolve_default_references=True) == {T1_d: str, T2_d: list[str]}
    assert alias_substitutions(A[()], resolve_default_references=True) == {T1_d: int, T2_d: list[int]}
    assert alias_substitutions(A[str, bytes]) == {T1_d: str, T2_d: bytes}


def test_type_alias_paramspec_default() -> None:
    P_d = ParamSpec('P_d', default=[T, int])
    A = TypeAliasType('A', Callable[P_d, T], type_params=(T, P_d))

    assert alias_substitutions(A[str]) == {T: str, P_d: (T, int)}
    assert alias_substitutions(A[str], resolve_default_references=True) == {T: str, P_d: (str, int)}
    assert alias_substitutions(A[str, [bool]]) == {T: str, P_d: (bool,)}


def test_type_alias_typevartuple() -> None:
    A = TypeAliasType('A', tuple[T, Unpack[Ts]], type_params=(T, Ts))

    assert alias_substitutions(A[int, str, bytes]) == {T: int, Ts: (str, bytes)}
    assert alias_substitutions(A[int]) == {T: int, Ts: ()}
    # Unpacked fixed-length tuples are expanded:
    assert alias_substitutions(A[int, Unpack[tuple[str, bytes]]]) == {T: int, Ts: (str, bytes)}


def test_type_alias_typevartuple_default() -> None:
    Ts_d = TypeVarTuple('Ts_d', default=Unpack[tuple[int, str]])
    A = TypeAliasType('A', tuple[T, Unpack[Ts_d]], type_params=(T, Ts_d))

    assert alias_substitutions(A[bool]) == {T: bool, Ts_d: (int, str)}
    assert alias_substitutions(A[bool, str]) == {T: bool, Ts_d: (str,)}


def test_type_alias_variadic_tuple_argument() -> None:
    A = TypeAliasType('A', tuple[Unpack[Ts], T], type_params=(Ts, T))

    # The unpacked arbitrary-length tuple provides a value for `T`, using its element type:
    substitutions = alias_substitutions(A[str, Unpack[tuple[int, Unpack[tuple[str, ...]]]]])
    assert substitutions[T] is str
    assert substitutions[Ts][:2] == (str, int)
    assert len(substitutions[Ts]) == 3


def test_too_few_arguments() -> None:
    A = TypeAliasType('A', tuple[T1, T2], type_params=(T1, T2))

    with pytest.raises(ValueError):
        alias_substitutions(A[int])


def test_variadic_tuple_argument_spanning_parameters() -> None:
    # Mirrors the runtime behavior for generic classes, where an unpacked arbitrary-length
    # tuple can't provide values for parameters on the other side of the `TypeVarTuple`:
    A = TypeAliasType('A', tuple[T1, Unpack[Ts], T2], type_params=(T1, Ts, T2))

    with pytest.raises(ValueError):
        alias_substitutions(A[int, Unpack[tuple[str, ...]]])


@pytest.mark.skipif(sys.version_info < (3, 12), reason='Requires new `type` statement syntax.')
def test_pep_695_syntax(create_module: Any) -> None:
    module = create_module(
        dedent("""
        from typing import Callable

        type A[T, *Ts] = tuple[T, *Ts]
        type B[**P] = Callable[P, int]

        class C[X, Y]: ...
        """)
    )

    T, Ts = module.A.__type_params__
    assert alias_substitutions(module.A[int, str, bytes]) == {T: int, Ts: (str, bytes)}
    assert alias_substitutions(module.A[int, *tuple[str, bytes]]) == {T: int, Ts: (str, bytes)}

    P = module.B.__type_params__[0]
    assert alias_substitutions(module.B[int, str]) == {P: (int, str)}

    X, Y = module.C.__type_params__
    assert alias_substitutions(module.C[int, str]) == {X: int, Y: str}


@pytest.mark.skipif(sys.version_info < (3, 13), reason='Requires the type parameter defaults syntax.')
def test_pep_695_syntax_defaults(create_module: Any) -> None:
    module = create_module(
        dedent("""
        from typing import Unpack

        type A[T1 = int, T2 = list[T1]] = tuple[T1, T2]
        type B[T, *Ts = Unpack[tuple[int, str]]] = tuple[T, *Ts]

        class C[X, Y = list[X]]: ...
        """)
    )

    T1, T2 = module.A.__type_params__
    assert alias_substitutions(module.A[str]) == {T1: str, T2: list[T1]}
    assert alias_substitutions(module.A[str], resolve_default_references=True) == {T1: str, T2: list[str]}

    T, Ts = module.B.__type_params__
    assert alias_substitutions(module.B[bool]) == {T: bool, Ts: (int, str)}

    # Same resolution for generic classes (the runtime applies the default, but
    # doesn't substitute `X` in it):
    X, Y = module.C.__type_params__
    assert alias_substitutions(module.C[str], resolve_default_references=True) == {X: str, Y: list[str]}
