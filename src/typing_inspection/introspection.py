"""High-level introspection utilities, used to inspect type annotations."""

from __future__ import annotations

import sys
import types
from collections import deque
from collections.abc import Generator, Sequence
from enum import Enum, IntEnum
from typing import Any, Literal, NamedTuple

from typing_extensions import TypeAlias, assert_never, get_origin

from . import typing_objects

__all__ = (  # noqa RUF022, order used by API docs
    'is_union_origin',
    'get_literal_values',
    'inspect_annotation',
    'AnnotationSource',
    'Qualifier',
    'InspectedAnnotation',
    'ForbiddenQualifier',
)

if sys.version_info >= (3, 10):

    def is_union_origin(obj: Any, /) -> bool:
        """Return whether the provided origin is the union form.

        >>> is_union_origin(typing.Union)
        True
        >>> is_union_origin(get_origin(int | str))
        True
        """
        return typing_objects.is_union(obj) or obj is types.UnionType

else:

    def is_union_origin(obj: Any, /) -> bool:
        """Return whether the provided origin is the union form.

        >>> is_union_origin(typing.Union)
        True
        >>> is_union_origin(get_origin(int | str))
        True
        """
        return typing_objects.is_union(obj)


def _literal_type_check(value: Any, /) -> None:
    """Type check the provided literal value against the `legal parameters`_.

    .. legal parameters: https://typing.readthedocs.io/en/latest/spec/literal.html#legal-parameters-for-literal-at-type-check-time.
    """
    if (
        not isinstance(value, (int, bytes, str, bool, Enum, typing_objects.NoneType))
        and value is not typing_objects.NoneType
    ):
        raise TypeError(f'{value} is not a valid literal value, must be one of: int, bytes, str, Enum, None.')


def get_literal_values(
    annotation: Any,
    /,
    *,
    type_check: bool = False,
    unpack_type_aliases: Literal['keep', 'lenient', 'eager'] = 'eager',
) -> Generator[Any]:
    """Yield the values contained in the provided :data:`~typing.Literal` :term:`tspec:special form`.

    Args:
        annotation: The :data:`~typing.Literal` :term:`tspec:special form` to unpack.
        type_check: Whether to check if the literal values are :ref:`legal parameters <tspec:literal-legal-parameters>`.
            Raises a :exc:`TypeError` otherwise.
        unpack_type_aliases: What to do when encountering :pep:`695` :ref:`type aliases <python:type-aliases>`.
            Can be one of:

            - :python:`"keep"`: Do not try to parse type aliases. Note that this can lead to incorrect results::

                >>> type MyAlias = Literal[1, 2]
                >>> list(get_literal_values(Literal[MyAlias, 3], unpack_type_aliases="keep"))
                [MyAlias, 3]

            - :python:`"lenient"`: Try to parse type aliases, and fallback to :python:`"keep"` if the type alias
              can't be inspected (because of an undefined forward reference).

            - :python:`"eager`: Parse type aliases and raise any encountered :exc:`NameError` exceptions (the default)::

                >>> type MyAlias = Literal[1, 2]
                >>> list(get_literal_values(Literal[MyAlias, 3], unpack_type_aliases="eager"))
                [1, 2, 3]

    Note:
        While :data:`None` is :ref:`equivalent to <tspec:none>` :python:`type(None)`, the runtime implementation of
        :data:`~typing.Literal` does not de-duplicate them. This function makes sure this de-duplication is applied::

            >>> list(get_literal_values(Literal[NoneType, None]))
            [None]

    Example:

        .. code-block:: pycon

            >>> type Ints = Literal[1, 2]
            >>> list(get_literal_values(Literal[1, Ints], expand_type_alias="keep"))
            ["a", Ints]
            >>> list(get_literal_values(Literal[1, Ints]))
            [1, 2]
            >>> list(get_literal_values(Literal[1.0], type_check=True))
            Traceback (most recent call last):
            ...
            TypeError: 1.0 is not a valid literal value, must be one of: int, bytes, str, Enum, None.
    """
    # `literal` is guaranteed to be a `Literal[...]` special form, so use
    # `__args__` directly instead of calling `get_args()`.

    if unpack_type_aliases == 'keep':
        _has_none = False
        # `Literal` parameters are already deduplicated, no need to do it ourselves.
        # (we only check for `None` and `NoneType`, which should be considered as duplicates).
        for arg in annotation.__args__:
            if type_check:
                _literal_type_check(arg)
            if arg is None or arg is typing_objects.NoneType:
                if not _has_none:
                    yield None
                _has_none = True
            else:
                yield arg
    else:
        # We'll need to manually deduplicate parameters, see the `Literal` implementation in `typing`.
        values_and_type: list[tuple[Any, type[Any]]] = []

        for arg in annotation.__args__:
            # Note: we could also check for generic aliases with a type alias as an origin.
            # However, it is very unlikely that this happens as type variables can't appear in
            # `Literal` forms, so the only valid (but unnecessary) use case would be something like:
            # `type Test[T] = Literal['a']` (and then use `Test[SomeType]`).
            if typing_objects.is_typealiastype(arg):
                try:
                    alias_value = arg.__value__
                except NameError:
                    if unpack_type_aliases == 'eager':
                        raise
                    # unpack_type_aliases == "lenient":
                    if type_check:
                        _literal_type_check(arg)
                    values_and_type.append((arg, type(arg)))
                else:
                    sub_args = get_literal_values(
                        alias_value, type_check=type_check, unpack_type_aliases=unpack_type_aliases
                    )
                    values_and_type.extend((a, type(a)) for a in sub_args)
            else:
                if type_check:
                    _literal_type_check(arg)
                values_and_type.append((None if arg is typing_objects.NoneType else arg, type(arg)))

        yield from (p for p, _ in dict.fromkeys(values_and_type))


Qualifier: TypeAlias = Literal['required', 'not_required', 'read_only', 'class_var', 'final']
"""A :term:`tspec:type qualifier`."""


# TODO at some point, we could switch to an enum flag, so that multiple sources
# can be combined. However, is there a need for this?
class AnnotationSource(IntEnum):
    # TODO if/when https://peps.python.org/pep-0767/ is accepted, add 'read_only'
    # to CLASS and NAMED_TUPLE (even though for named tuples it is redundant).

    """The source of an annotation, e.g. a class or a function.

    Depending on the source, different :term:`type qualifiers <tspec:type qualifier>` may be (dis)allowed.
    """

    ASSIGNMENT_OR_VARIABLE = 1
    """An annotation used in an assignment or variable annotation::

        x: Final[int] = 1
        y: Final[str]

    **Allowed type qualifiers:** :data:`~typing.Final`.
    """

    CLASS = 2
    """An annotation used in the body of a class::

        class Test:
            x: Final[int] = 1
            y: ClassVar[str]

    **Allowed type qualifiers:** :data:`~typing.ClassVar`, :data:`~typing.Final`.
    """

    TYPED_DICT = 3
    """An annotation used in the body of a :class:`~typing.TypedDict`::

        class TD(TypedDict):
            x: Required[ReadOnly[int]]
            y: ReadOnly[NotRequired[str]]

    **Allowed type qualifiers:** :data:`~typing.ReadOnly`, :data:`~typing.Required`, :data:`~typing.NotRequired`.
    """

    NAMED_TUPLE = 4
    """An annotation used in the body of a :class:`~typing.NamedTuple`.

        class NT(NamedTuple):
            x: int
            y: str

    **Allowed type qualifiers:** none.
    """

    FUNCTION = 5
    """An annotation used in a function, either for a parameter or the return value.

        def func(a: int) -> str:
            ...

    **Allowed type qualifiers:** none.
    """

    ANY = 6
    """An annotation that might come from any source.

    **Allowed type qualifiers:** all.
    """

    BARE = 7
    """An annotation that is inspected as is.

    **Allowed type qualifiers:** none.
    """

    @property
    def allowed_qualifiers(self) -> set[Qualifier]:
        """The allowed :term:`type qualifiers <tspec:type qualifier>` for this annotation source."""
        # TODO use a match statement when Python 3.9 support is dropped.
        if self is AnnotationSource.ASSIGNMENT_OR_VARIABLE:
            return {'final'}
        elif self is AnnotationSource.CLASS:
            return {'final', 'class_var'}
        elif self is AnnotationSource.TYPED_DICT:
            return {'required', 'not_required', 'read_only'}
        elif self in (AnnotationSource.NAMED_TUPLE, AnnotationSource.FUNCTION, AnnotationSource.BARE):
            return set()
        elif self is AnnotationSource.ANY:
            return {'required', 'not_required', 'read_only', 'class_var', 'final'}
        else:
            assert_never(self)


class ForbiddenQualifier(Exception):
    """The provided :term:`tspec:type qualifier` is forbidden."""

    def __init__(self, qualifier: Qualifier, /) -> None:
        self.qualifier = qualifier


class InspectedAnnotation(NamedTuple):
    """The result of the inspected annotation."""

    type: Any
    """The final :term:`tspec:annotation expression`, with :term:`type qualifiers <tspec:type qualifier>`
    and annotated metadata stripped.
    """

    qualifiers: set[Qualifier]
    """The :term:`type qualifiers <tspec:type qualifier>` present on the annotation."""

    metadata: Sequence[Any]
    """The annotated metadata."""


def inspect_annotation(
    annotation: Any,
    /,
    *,
    annotation_source: AnnotationSource,
    unpack_type_aliases: Literal['keep', 'lenient', 'eager'] = 'eager',
) -> InspectedAnnotation:
    """Inspect an :term:`tspec:annotation expression`, extracting any :term:`tspec:type qualifier` and metadata.

    An :term:`tspec:annotation expression` is a :term:`tspec:type expression` optionally surrounded by one or more
    :term:`type qualifiers <tspec:type qualifier>` or by :data:`~typing.Annotated`. This function will:

    - Unwrap the type expression, keeping track of the type qualifiers.
    - Unwrap :data:`~typing.Annotated` forms, keeping track of the annotated metadata.

    Args:
        annotation: The annotation expression to be inspected.
        annotation_source: The source of the annotation. Depending on the source (e.g. a class), different type
            qualifiers may be (dis)allowed. To allow any type qualifier, use :attr:`AnnotationSource.ANY`.
        unpack_type_aliases: What to do when encountering :pep:`695` :ref:`type aliases <python:type-aliases>`.
            Can be one of:

            - :python:`"keep"`: Do not try to parse type aliases. Note that this can lead to incorrect results::

                >>> type MyInt = Annotated[int, "meta"]
                >>> inspect_annotation(MyInt, annotation_source=AnnotationSource.BARE, unpack_type_aliases="keep")
                InspectedAnnotation(type=MyInt, qualifiers={}, metadata=[])

            - :python:`"lenient"`: Try to parse type aliases, and fallback to :python:`"keep"` if the type alias
              can't be inspected (because of an undefined forward reference)::

                >>> type MyInt = Annotated[Undefined, "meta"]
                >>> inspect_annotation(MyInt, annotation_source=AnnotationSource.BARE, unpack_type_aliases="lenient")
                InspectedAnnotation(type=MyInt, qualifiers={}, metadata=[])
                >>> Undefined = int
                >>> inspect_annotation(MyInt, annotation_source=AnnotationSource.BARE, unpack_type_aliases="lenient")
                InspectedAnnotation(type=int, qualifiers={}, metadata=["meta"])

            - :python:`"eager`: Parse type aliases and raise any encountered :exc:`NameError` exceptions (the default).

    Returns:
        The result of the inspected annotation, where the type expression, used qualifiers and metadata is stored.
    """
    allowed_qualifiers = annotation_source.allowed_qualifiers
    qualifiers: set[Qualifier] = set()
    metadata: deque[Any] = deque()

    while True:
        annotation, _meta = _unpack_annotated(annotation, unpack_type_aliases=unpack_type_aliases)
        if _meta:
            # Equivalent to metadata = _meta + metadata,
            # but way faster:
            metadata.extendleft(reversed(_meta))
            continue

        origin = get_origin(annotation)
        if origin is not None:
            if typing_objects.is_classvar(origin):
                if 'class_var' not in allowed_qualifiers:
                    raise ForbiddenQualifier('class_var')
                qualifiers.add('class_var')
                annotation = annotation.__args__[0]
            elif typing_objects.is_final(origin):
                if 'final' not in allowed_qualifiers:
                    raise ForbiddenQualifier('final')
                qualifiers.add('final')
                annotation = annotation.__args__[0]
            elif typing_objects.is_required(origin):
                if 'required' not in allowed_qualifiers:
                    raise ForbiddenQualifier('required')
                qualifiers.add('required')
                annotation = annotation.__args__[0]
            elif typing_objects.is_notrequired(origin):
                if 'not_required' not in allowed_qualifiers:
                    raise ForbiddenQualifier('not_required')
                qualifiers.add('not_required')
                annotation = annotation.__args__[0]
            elif typing_objects.is_readonly(origin):
                if 'read_only' not in allowed_qualifiers:
                    raise ForbiddenQualifier('not_required')
                qualifiers.add('read_only')
                annotation = annotation.__args__[0]
            else:
                # origin is not None but not a type qualifier nor `Annotated` (e.g. `list[int]`):
                break

    # `Final` is the only type qualifier allowed to be used as a bare annotation
    # (`ClassVar` is under discussion):
    if typing_objects.is_final(annotation):
        if 'final' not in allowed_qualifiers:
            raise ForbiddenQualifier('final')
        qualifiers.add('final')
        # TODO if the annotation comes from an annotated assigment, we should
        # infer the annotation from the assigned value (see
        # https://typing.readthedocs.io/en/latest/spec/qualifiers.html#syntax).
        # To do so, we could have a special `Infer` sentinel, or require
        # `inspect_annotation` to take the assigned value.
        annotation = Any

    return InspectedAnnotation(annotation, qualifiers, metadata)


def _unpack_annotated_inner(
    annotation, unpack_type_aliases: Literal['lenient', 'eager'], check_annotated: bool
) -> tuple[Any, list[Any]]:
    origin = get_origin(annotation)
    if check_annotated and typing_objects.is_annotated(origin):
        annotated_type = annotation.__origin__
        metadata = list(annotation.__metadata__)

        # The annotated type might be a PEP 695 type alias, so we need to recursively
        # unpack it. Because Python already flattens `Annotated[Annotated[<type>, ...], ...]` forms,
        # we can skip the `is_annotated()` check in the next call:
        annotated_type, sub_meta = _unpack_annotated_inner(
            annotated_type, unpack_type_aliases=unpack_type_aliases, check_annotated=False
        )
        metadata = sub_meta + metadata
        return annotated_type, metadata
    elif typing_objects.is_typealiastype(annotation):
        try:
            value = annotation.__value__
        except NameError:
            if unpack_type_aliases == 'eager':
                raise
        else:
            typ, metadata = _unpack_annotated_inner(
                value, unpack_type_aliases=unpack_type_aliases, check_annotated=True
            )
            if metadata:
                # Having metadata means the type alias' `__value__` was an `Annotated` form
                # (or, recursively, a type alias to an `Annotated` form). It is important to check
                # for this, as we don't want to unpack other type aliases (e.g. `type MyInt = int`).
                return typ, metadata
            return annotation, []
    elif typing_objects.is_typealiastype(origin):
        # When parameterized, PEP 695 type aliases become generic aliases
        # (e.g. with `type MyList[T] = Annotated[list[T], ...]`, `MyList[int]`
        # is a generic alias).
        try:
            value = origin.__value__
        except NameError:
            if unpack_type_aliases == 'eager':
                raise
        else:
            # While Python already handles type variable replacement for simple `Annotated` forms,
            # we need to manually apply the same logic for PEP 695 type aliases:
            # - With `MyList = Annotated[list[T], ...]`, `MyList[int] == Annotated[list[int], ...]`
            # - With `type MyList[T] = Annotated[list[T], ...]`, `MyList[int].__value__ == Annotated[list[T], ...]`.

            try:
                # To do so, we emulate the parameterization of the value with the arguments:
                # with `type MyList[T] = Annotated[list[T], ...]`, to emulate `MyList[int]`,
                # we do `Annotated[list[T], ...][int]` (which gives `Annotated[list[T], ...]`):
                value = value[annotation.__args__]
            except TypeError:
                # Might happen if the type alias is parameterized, but its value doesn't have any
                # type variables, e.g. `type MyInt[T] = int`.
                pass
            typ, metadata = _unpack_annotated_inner(
                value, unpack_type_aliases=unpack_type_aliases, check_annotated=True
            )
            if metadata:
                return typ, metadata
            return annotation, []

    return annotation, []


# This could eventually be made public:
def _unpack_annotated(
    annotation: Any, /, *, unpack_type_aliases: Literal['keep', 'lenient', 'eager'] = 'eager'
) -> tuple[Any, list[Any]]:
    if unpack_type_aliases == 'keep':
        if typing_objects.is_annotated(get_origin(annotation)):
            return annotation.__origin__, list(annotation.__metadata__)
        else:
            return annotation, []

    return _unpack_annotated_inner(annotation, unpack_type_aliases=unpack_type_aliases, check_annotated=True)
