import sys
import typing as t
from textwrap import dedent
from typing import Any

import pytest
import typing_extensions as t_e

from typing_inspection import typing_objects
from typing_inspection.introspection import get_literal_values

TypingAlias = t_e.TypeAliasType('TypingAlias', t.Literal[1, 'a'])


@pytest.mark.parametrize(
    ['annotation', 'expected'],
    [
        (t.Literal[1, 'a'], [1, 'a']),
        (t.Literal[1, 'a'], [1, 'a']),
        (t.Literal[1, TypingAlias], [1, TypingAlias]),
    ],
)
def test_literal_values_skip_aliases_no_type_check(annotation: Any, expected: list[Any]) -> None:
    result = get_literal_values(annotation, type_check=False, unpack_type_aliases='skip')
    assert list(result) == expected


def test_literal_values_skip_aliases_type_check() -> None:
    with pytest.raises(TypeError):
        list(get_literal_values(t.Literal[1, TypingAlias], type_check=True, unpack_type_aliases='skip'))


def test_literal_values_type_check() -> None:
    literal = t.Literal[1, True, False, b'', '', None, typing_objects.NoneType]  # noqa: PYI061
    expected = [1, True, False, b'', '', None]
    assert list(get_literal_values(literal, type_check=True, unpack_type_aliases='skip')) == expected
    assert list(get_literal_values(literal, type_check=True, unpack_type_aliases='eager')) == expected

    with pytest.raises(TypeError):
        list(get_literal_values(t.Literal[1.0], type_check=True, unpack_type_aliases='skip'))

    with pytest.raises(TypeError):
        list(get_literal_values(t.Literal[1.0], type_check=True, unpack_type_aliases='eager'))


def test_literal_values_unpack_type_aliases() -> None:
    TestType0 = t_e.TypeAliasType('TestType0', t_e.Literal['a'])
    TestType1 = t_e.TypeAliasType('TestType1', t_e.Literal[TestType0, 'b'])
    TestType2 = t_e.TypeAliasType('TestType2', t.Literal[TestType1, 'c'])

    expected = ['a', 'b', 'c', 'd']

    assert list(get_literal_values(t.Literal[TestType2, 'd'], unpack_type_aliases='eager')) == expected


@pytest.mark.parametrize('unpack_mode', ['eager', 'lenient'])
@pytest.mark.parametrize('type_check', [False, True])
def test_literal_values_unpack_alias_chain(unpack_mode, type_check: bool) -> None:
    Status = t_e.TypeAliasType('Status', t.Literal[1, True, typing_objects.NoneType, 'queued'])
    ExportedStatus = t_e.TypeAliasType('ExportedStatus', Status)
    PublicStatus = t_e.TypeAliasType('PublicStatus', ExportedStatus)
    AllStatus = t_e.TypeAliasType('AllStatus', t.Literal[PublicStatus, 'done', 1, None])  # noqa: PYI061

    result = list(
        get_literal_values(
            t.Literal[AllStatus, ExportedStatus, 'cancelled'],
            type_check=type_check,
            unpack_type_aliases=unpack_mode,
        )
    )
    expected = [1, True, None, 'queued', 'done', 'cancelled']
    assert [(value, type(value)) for value in result] == [(value, type(value)) for value in expected]


def test_literal_values_skip_alias_chain() -> None:
    Status = t_e.TypeAliasType('Status', t.Literal['queued', 'done'])
    ExportedStatus = t_e.TypeAliasType('ExportedStatus', Status)
    literal = t.Literal[ExportedStatus, 'cancelled']

    assert list(get_literal_values(literal, unpack_type_aliases='skip')) == [ExportedStatus, 'cancelled']
    with pytest.raises(TypeError):
        list(get_literal_values(literal, type_check=True, unpack_type_aliases='skip'))


@pytest.mark.parametrize('unpack_mode', ['eager', 'lenient'])
def test_literal_values_alias_chain_type_check(unpack_mode) -> None:
    Invalid = t_e.TypeAliasType('Invalid', t.Literal[1.5])
    ExportedInvalid = t_e.TypeAliasType('ExportedInvalid', Invalid)

    assert list(get_literal_values(t.Literal[ExportedInvalid], unpack_type_aliases=unpack_mode)) == [1.5]
    with pytest.raises(TypeError, match=r'1\.5 is not a valid literal value'):
        list(get_literal_values(t.Literal[ExportedInvalid], type_check=True, unpack_type_aliases=unpack_mode))


@pytest.mark.skipif(sys.version_info < (3, 12), reason='Requires new `type` statement syntax.')
@pytest.mark.parametrize('unpack_mode', ['eager', 'lenient', 'skip'])
def test_literal_values_native_alias_chain(create_module, unpack_mode) -> None:
    module = create_module(
        dedent("""
    from typing import Literal

    type Status = Literal['queued', 'done']
    type ExportedStatus = Status
    type PublicStatus = ExportedStatus
    """)
    )

    expected = [module.PublicStatus, 'cancelled'] if unpack_mode == 'skip' else ['queued', 'done', 'cancelled']
    assert (
        list(get_literal_values(t.Literal[module.PublicStatus, 'cancelled'], unpack_type_aliases=unpack_mode))
        == expected
    )


@pytest.mark.skipif(sys.version_info < (3, 12), reason='Requires new `type` statement syntax.')
def test_literal_values_alias_chain_undefined(create_module) -> None:
    module = create_module(
        dedent("""
    from typing import Literal

    type Status = Undefined
    type ExportedStatus = Status
    type AllStatus = Literal['queued', ExportedStatus]
    """)
    )
    literal = t.Literal[module.AllStatus, 'cancelled']

    assert list(get_literal_values(literal, unpack_type_aliases='lenient')) == [
        'queued',
        module.ExportedStatus,
        'cancelled',
    ]
    with pytest.raises(NameError, match='Undefined'):
        list(get_literal_values(literal, unpack_type_aliases='eager'))
    with pytest.raises(TypeError):
        list(get_literal_values(literal, type_check=True, unpack_type_aliases='lenient'))

    module.Undefined = t.Literal['done']
    assert list(get_literal_values(literal)) == ['queued', 'done', 'cancelled']


@pytest.mark.skipif(sys.version_info < (3, 12), reason='Requires new `type` statement syntax.')
def test_literal_values_unpack_type_aliases_undefined(create_module) -> None:
    code = dedent("""
    from typing import Literal

    type TestType0 = Literal[Undefined, 'a']
    type TestType1 = Literal[TestType0, 'b']
    """)

    module = create_module(code)
    expected = [module.TestType0, 'b', 'c']

    assert list(get_literal_values(t.Literal[module.TestType1, 'c'], unpack_type_aliases='lenient')) == expected

    with pytest.raises(NameError):
        list(get_literal_values(t.Literal[module.TestType1, 'c'], unpack_type_aliases='eager'))

    with pytest.raises(TypeError):
        # As `TestType0` can't be unpacked, it isn't a valid literal value:
        list(get_literal_values(t.Literal[module.TestType1, 'c'], type_check=True, unpack_type_aliases='lenient'))


def test_literal_values_unhashable_type() -> None:
    assert list(get_literal_values(t_e.Literal[[1, 'a']])) == [[1, 'a']]


@pytest.mark.skipif(
    sys.version_info >= (3, 13, 15),
    reason='Unashable arguments are deduplicated (https://github.com/python/cpython/pull/153914)',
)
def test_duplicate_literal_values_unhashable_type() -> None:
    assert list(get_literal_values(t_e.Literal[[1, 'a'], [1, 'a']])) == [[1, 'a'], [1, 'a']]  # noqa: PYI062
