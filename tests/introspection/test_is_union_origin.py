import sys
import types
import typing
from typing import Any

import pytest
import typing_extensions

from typing_inspection.introspection import is_union_origin

unions: list[Any] = [
    typing.Union,
    typing_extensions.Union,
]

if sys.version_info >= (3, 10):
    unions.append(types.UnionType)


@pytest.mark.parametrize(
    'union',
    unions,
)
def test_is_union_origin(union: Any) -> None:
    assert is_union_origin(union)
