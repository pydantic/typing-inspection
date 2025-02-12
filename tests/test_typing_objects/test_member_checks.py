import collections
import sys
import types
import typing
from collections.abc import Callable
from typing import Any, NewType, TypeVar

import pytest
import typing_extensions
from typing_extensions import ParamSpec, ParamSpecArgs, ParamSpecKwargs, TypeAlias, TypeAliasType, TypeVarTuple

from typing_inspection import typing_objects

CheckFunction: TypeAlias = Callable[[Any], bool]


names_and_functions: list[tuple[str, CheckFunction]] = [
    ('Annotated', typing_objects.is_annotated),
    ('Any', typing_objects.is_any),
    ('ClassVar', typing_objects.is_classvar),
    ('Concatenate', typing_objects.is_concatenate),
    ('Final', typing_objects.is_final),
    ('Generic', typing_objects.is_generic),
    ('Literal', typing_objects.is_literal),
    ('LiteralString', typing_objects.is_literalstring),
    ('Never', typing_objects.is_never),
    ('NoDefault', typing_objects.is_nodefault),
    ('NoReturn', typing_objects.is_noreturn),
    ('NotRequired', typing_objects.is_notrequired),
    ('ReadOnly', typing_objects.is_readonly),
    ('Required', typing_objects.is_required),
    ('Self', typing_objects.is_self),
    ('TypeAlias', typing_objects.is_typealias),
    ('TypeGuard', typing_objects.is_typeguard),
    ('TypeIs', typing_objects.is_typeis),
    ('Union', typing_objects.is_union),
    ('Unpack', typing_objects.is_unpack),
]


identity_member_checks: list[tuple[CheckFunction, Any, bool]] = []

for typing_name, function in names_and_functions:
    if hasattr(typing, typing_name):
        identity_member_checks.append((function, getattr(typing, typing_name), True))
    if hasattr(typing_extensions, typing_name):
        identity_member_checks.append((function, getattr(typing_extensions, typing_name), True))


@pytest.mark.parametrize(
    ['function', 'member', 'result'],
    identity_member_checks,
)
def test_identity_member_check(function: CheckFunction, member: Any, result: bool) -> None:
    assert function(member) == result


class TypingNamedTuple(typing.NamedTuple):
    pass


class TypingExtensionsNamedTuple(typing_extensions.NamedTuple):
    pass


CollectionsNamedTuple = collections.namedtuple('CollectionsNamedTuple', [])  # pyright: ignore[reportUntypedNamedTuple]  # noqa: PYI024


@pytest.mark.parametrize('nt_class', [TypingNamedTuple, TypingExtensionsNamedTuple, CollectionsNamedTuple])
def test_is_namedtuple(nt_class: type[Any]) -> None:
    assert typing_objects.is_namedtuple(nt_class)


TypingNewType = typing.NewType('TypingNewType', int)
TypingExtensionsNewType = typing.NewType('TypingExtensionsNewType', str)


@pytest.mark.parametrize(
    'new_type',
    [TypingNewType, TypingExtensionsNewType],
)
def test_is_newtype(new_type: NewType) -> None:
    assert typing_objects.is_newtype(new_type)


TypingExtensionsP = typing_extensions.ParamSpec('TypingExtensionsP')

param_specs: list[ParamSpec] = [TypingExtensionsP]
if sys.version_info >= (3, 10):
    TypingP = typing.ParamSpec('TypingP')
    param_specs.append(TypingP)


@pytest.mark.parametrize(
    'param_spec',
    param_specs,
)
def test_is_paramspec(param_spec: ParamSpec) -> None:
    assert typing_objects.is_paramspec(param_spec)


@pytest.mark.parametrize(
    'param_spec_args',
    [p.args for p in param_specs],
)
def test_is_paramspecargs(param_spec_args: ParamSpecArgs) -> None:
    assert typing_objects.is_paramspecargs(param_spec_args)


@pytest.mark.parametrize(
    'param_spec_kwargs',
    [p.kwargs for p in param_specs],
)
def test_is_paramspeckwargs(param_spec_kwargs: ParamSpecKwargs) -> None:
    assert typing_objects.is_paramspeckwargs(param_spec_kwargs)


T = TypeVar('T')

TypingExtensionsTypeAliasType = typing_extensions.TypeAliasType('TypingExtensionsTypeAliasType', int, type_params=(T,))

type_alias_types: list[TypeAliasType] = []
if sys.version_info >= (3, 12):
    TypingTypeAliasType = typing_extensions.TypeAliasType('TypingTypeAliasType', int, type_params=(T,))
    type_alias_types.append(TypingTypeAliasType)


@pytest.mark.parametrize(
    'type_alias_type',
    type_alias_types,
)
def test_is_typealiastype(type_alias_type: TypeAliasType) -> None:
    assert typing_objects.is_typealiastype(type_alias_type)

    # See Python 3.10 comment in the implementation:
    assert not typing_objects.is_typealiastype(type_alias_type[int])


TypingTypeVar = typing.TypeVar('TypingTypeVar')
TypingExtensionsTypeVar = typing_extensions.TypeVar('TypingExtensionsTypeVar')


@pytest.mark.parametrize(
    'type_var',
    [TypingTypeVar, TypingExtensionsTypeVar],
)
def test_is_typevar(type_var: TypeVar) -> None:
    assert typing_objects.is_typevar(type_var)


TypingExtensionsTypeVarTuple = typing_extensions.TypeVarTuple('TypingExtensionsTypeVarTuple')

type_var_tuples: list[TypeVarTuple] = []

if sys.version_info >= (3, 11):
    TypingTypeVarTuple = typing.TypeVarTuple('TypingTypeVarTuple')
    type_var_tuples.append(TypingTypeVarTuple)


@pytest.mark.parametrize(
    'type_var_tuple',
    type_var_tuples,
)
def test_is_typevartuple(type_var_tuple: TypeVarTuple) -> None:
    assert typing_objects.is_typevartuple(type_var_tuple)


# Misc. tests:


@pytest.mark.skipif(sys.version_info < (3, 10), reason='`types.UnionType` is only available in Python 3.10.')
def test_is_union_does_not_match_uniontype() -> None:
    assert not typing_objects.is_union(types.UnionType)
