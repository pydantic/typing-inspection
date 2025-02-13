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
    literal = t.Literal[1, True, False, b'', '', None, typing_objects.NoneType]
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
