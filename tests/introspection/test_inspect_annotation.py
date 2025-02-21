import sys
import typing as t
from textwrap import dedent
from typing import Any, Literal

import pytest
import typing_extensions as t_e

from typing_inspection.introspection import INFERRED, AnnotationSource, ForbiddenQualifier, inspect_annotation

_all_qualifiers: list[Any] = [
    t_e.ClassVar[int],
    t_e.Final[int],
    t_e.ReadOnly[int],
    t_e.Required[int],
    t_e.NotRequired[int],
]


@pytest.mark.parametrize(
    ['source', 'annotations'],
    [
        (AnnotationSource.ASSIGNMENT_OR_VARIABLE, [t_e.Final[int]]),
        (AnnotationSource.CLASS, [t_e.ClassVar[int], t.Final[int]]),
        (AnnotationSource.TYPED_DICT, [t_e.ReadOnly[int], t_e.Required[int], t_e.NotRequired[int]]),
        (AnnotationSource.ANY, _all_qualifiers),
    ],
)
def test_annotation_source_valid_qualifiers(source: AnnotationSource, annotations: list[Any]) -> None:
    for annotation in annotations:
        assert inspect_annotation(annotation, annotation_source=source).type is int


@pytest.mark.parametrize(
    ['source', 'annotations'],
    [
        (
            AnnotationSource.ASSIGNMENT_OR_VARIABLE,
            [t_e.ClassVar[int], t_e.ReadOnly[int], t_e.Required[int], t_e.NotRequired[int]],
        ),
        (AnnotationSource.CLASS, [t_e.ReadOnly[int], t_e.Required[int], t_e.NotRequired[int]]),
        (AnnotationSource.TYPED_DICT, [t_e.ClassVar[int], t_e.Final[int]]),
        (AnnotationSource.NAMED_TUPLE, _all_qualifiers),
        (AnnotationSource.FUNCTION, _all_qualifiers),
        (AnnotationSource.BARE, _all_qualifiers),
    ],
)
def test_annotation_source_invalid_qualifiers(source: AnnotationSource, annotations: list[Any]) -> None:
    for annotation in annotations:
        with pytest.raises(ForbiddenQualifier):
            inspect_annotation(annotation, annotation_source=source)


def test_bare_final_qualifier() -> None:
    result = inspect_annotation(
        t.Final,
        annotation_source=AnnotationSource.ANY,
    )

    assert result.qualifiers == {'final'}
    assert result.type is INFERRED


def test_nested_metadata_and_qualifiers() -> None:
    result = inspect_annotation(
        t_e.Final[t_e.Annotated[t_e.ClassVar[t_e.Annotated[int, 1]], 2]],  # pyright: ignore[reportInvalidTypeForm]
        annotation_source=AnnotationSource.ANY,
    )

    assert result.type is int
    assert result.qualifiers == {'class_var', 'final'}
    assert result.metadata == [1, 2]


Alias1 = t_e.TypeAliasType('Alias1', t_e.Annotated[t_e.ReadOnly[int], 1])  # pyright: ignore[reportInvalidTypeForm]
Alias2 = t_e.TypeAliasType('Alias2', t_e.Annotated[t_e.Required[Alias1], 2])  # pyright: ignore[reportInvalidTypeForm]


@pytest.mark.parametrize(
    'unpack_mode',
    ['eager', 'lenient'],
)
def test_unpack_type_aliases(unpack_mode: Literal['eager', 'lenient']) -> None:
    result = inspect_annotation(
        t_e.Final[t_e.Annotated[t_e.ClassVar[t_e.Annotated[Alias2, 3]], 4]],  # pyright: ignore[reportInvalidTypeForm]
        annotation_source=AnnotationSource.ANY,
        unpack_type_aliases=unpack_mode,
    )

    assert result.type is int
    assert result.qualifiers == {'read_only', 'required', 'class_var', 'final'}
    assert result.metadata == [1, 2, 3, 4]


T = t.TypeVar('T')

InnerList = t_e.TypeAliasType('InnerList', t.Annotated[list[T], 1], type_params=(T,))
MyList = t_e.TypeAliasType('MyList', t.Annotated[InnerList[T], 2], type_params=(T,))
MyIntList = t_e.TypeAliasType('MyIntList', MyList[int])


@pytest.mark.parametrize(
    'unpack_mode',
    ['eager', 'lenient'],
)
def test_unpack_type_aliases_generic(unpack_mode: Literal['eager', 'lenient']) -> None:
    result = inspect_annotation(
        MyIntList,
        annotation_source=AnnotationSource.ANY,
        unpack_type_aliases=unpack_mode,
    )

    assert result.type == list[int]
    assert result.metadata == [1, 2]


@pytest.mark.skipif(sys.version_info < (3, 12), reason='Requires new `type` statement syntax.')
def test_unpack_type_aliases_undefined_eager_fails(create_module) -> None:
    code = dedent("""
    from typing import Annotated

    type TestType0 = Annotated[Undefined, 1]
    type TestType1 = Annotated[TestType0, 2]
    """)

    module = create_module(code)

    with pytest.raises(NameError) as exc_info:
        inspect_annotation(
            module.TestType1,
            annotation_source=AnnotationSource.ANY,
            unpack_type_aliases='eager',
        )

    if sys.version_info >= (3, 10):
        assert exc_info.value.name == 'Undefined'


@pytest.mark.skipif(sys.version_info < (3, 12), reason='Requires new `type` statement syntax.')
def test_unpack_type_aliases_undefined_lenient(create_module) -> None:
    code = dedent("""
    from typing import Annotated

    type TestType0 = Annotated[Undefined, 1]
    type TestType1 = Annotated[TestType0, 2]
    """)

    module = create_module(code)

    result = inspect_annotation(
        t.Annotated[t.Final[module.TestType1], 3],
        annotation_source=AnnotationSource.ANY,
        unpack_type_aliases='lenient',
    )

    assert result.type is module.TestType0
    assert result.qualifiers == {'final'}
    assert result.metadata == [2, 3]
