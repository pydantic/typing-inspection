import collections.abc
import sys
import types
from typing import (  # noqa: UP035
    Annotated,
    Any,
    Callable,
    ClassVar,
    Generic,
    Literal,
    Optional,
    TypeVar,
    Union,
    get_origin,
)

import pytest

from typing_inspection.introspection._parsing import InvalidExpression, TypeHintTransformer, TypeHintVisitor

T = TypeVar('T')


class ReplaceInt(TypeHintTransformer):
    def visit_bare_annotation_expr(self, annotation_expr: Any) -> Any:
        if annotation_expr is int:
            return str
        return super().visit_bare_annotation_expr(annotation_expr)


@pytest.mark.parametrize(
    'annotation_expr',
    [
        str,
        list[str],
        list[list[str]],
        Optional[str],  # noqa: UP045
        str | None,
        Union[str, bytes],  # noqa: UP007
        Literal[1],
        Callable[[str], str],
        collections.abc.Callable[[str], str],
        Annotated[str, 'meta'],
        ClassVar[str],
        tuple[str, ...],
        TypeVar('U'),
    ],
    ids=repr,
)
def test_transformer_unchanged_identity(annotation_expr: Any) -> None:
    """When nothing changes, the exact same object is returned."""
    assert ReplaceInt().visit(annotation_expr) is annotation_expr


@pytest.mark.parametrize(
    ['annotation_expr', 'expected'],
    [
        (int, str),
        (list[int], list[str]),
        (list[list[int]], list[list[str]]),
        (dict[str, int], dict[str, str]),
        (Optional[int], Optional[str]),  # noqa: UP045
        (int | None, str | None),
        (Union[int, bytes], Union[str, bytes]),  # noqa: UP007
        (Callable[[int], int], Callable[[str], str]),
        (Callable[..., int], Callable[..., str]),
        (collections.abc.Callable[[int], int], collections.abc.Callable[[str], str]),
        (Annotated[int, 'meta'], Annotated[str, 'meta']),
        (ClassVar[int], ClassVar[str]),
        (tuple[int, ...], tuple[str, ...]),
        (Literal[1], Literal[1]),
        (type[int], type[str]),
    ],
    ids=repr,
)
def test_transformer_replacement(annotation_expr: Any, expected: Any) -> None:
    transformed = ReplaceInt().visit(annotation_expr)
    assert transformed == expected
    assert type(transformed) is type(expected)


def test_union_type_preserved() -> None:
    transformed = ReplaceInt().visit(int | None)
    if sys.version_info >= (3, 14):
        assert transformed == Union[str, None]  # noqa: UP007
    else:
        assert isinstance(transformed, types.UnionType)


def test_generic_invalid() -> None:
    with pytest.raises(InvalidExpression):
        TypeHintVisitor().visit(Generic)
    with pytest.raises(InvalidExpression):
        TypeHintVisitor().visit(Generic[T])


def test_visitor_fast_paths() -> None:
    """Common annotation expressions dispatch to the right visitor method."""

    class Recorder(TypeHintVisitor):
        def __init__(self) -> None:
            self.bare: list[Any] = []
            self.parameterized: list[tuple[Any, Any]] = []

        def visit_bare_annotation_expr(self, annotation_expr: Any) -> Any:
            self.bare.append(annotation_expr)

        def visit_parameterized_annotation_expr(self, annotation_expr: Any, origin: Any) -> Any:
            self.parameterized.append((annotation_expr, origin))
            return super().visit_parameterized_annotation_expr(annotation_expr, origin)

    class Meta(type): ...

    class WithMeta(metaclass=Meta): ...

    recorder = Recorder()
    recorder.visit(dict[str, list[WithMeta]] | None)
    assert recorder.bare == [str, WithMeta, type(None)]
    assert [origin for _, origin in recorder.parameterized] == [get_origin(int | str), dict, list]
