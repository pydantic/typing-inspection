import sys
import typing as t

import pytest
import typing_extensions as t_e

from typing_inspection.introspection import AnnotationSource, inspect_annotation

# Proper tests should be written out in the future.

Alias = t_e.TypeAliasType('Alias', t.Annotated[int, 1])


@pytest.mark.skipif(sys.version_info < (3, 10), reason='Runtime error with annotated')
def test_unpack_annotation() -> None:
    result = inspect_annotation(
        t.Final[t.Annotated[t.ClassVar[t.Annotated[Alias, 2]], 3]],
        annotation_source=AnnotationSource.ANY,
    )

    assert result.type is int
    assert result.qualifiers == {'class_var', 'final'}
    assert list(result.metadata) == [1, 2, 3]
