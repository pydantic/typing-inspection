.. _usage:

Usage
=====

The library is divided into two submodules:

- :mod:`typing_inspection.typing_objects`: provides functions to check if a variable is a :mod:`typing` object::

    from typing_extensions import Union, get_origin

    from typing_inspection.typing_objects import is_union

    is_union(get_origin(Union[int, str]))  # True

  .. note::

    You might be tempted to use a simple identity check::

        >>> get_origin(Union[int, str]) is typing.Union

    However, :mod:`typing_extensions` might provide a different version of the :mod:`typing` objects. Instead,
    the :mod:`~typing_inspection.typing_objects` functions make sure to check against both variants, if they are
    different.

- :mod:`typing_inspection.introspection`: provides high-level introspection functions, taking runtime edge cases
  into account.

Inspecting annotations
----------------------

If, as a library, you rely heavily on type hints, you may encounter subtle unexpected behaviors and performance
issues when inspecting annotations. As such, this section provides a recommended workflow to do so.

Fetching type hints
^^^^^^^^^^^^^^^^^^^

The first step is to gather the type annotations from the object you want to inspect. The :func:`typing.get_type_hints`
function can be used to do so. If you want to make use of annotated metadata, make sure to set the ``include_extras``
argument to :python:`True`.

.. code-block:: pycon

    >>> class A:
    ...    x: int
    ...    y: Annotated[int, ...]
    ...
    >>> get_type_hints(A, include_extras=True)
    {'x': int, 'y': Annotated[int, ...]}

.. note::

    Currently, ``typing-inspection`` does not provide any utility to fetch (and evaluate) type annotations. The current
    :mod:`typing` utilities might contain subtle bugs across the different Python versions, so there is value in
    having similar functionality. It might be best to wait for :pep:`649` to be fully implemented first.

Unpacking metadata and qualifiers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The annotations fetched in the previous step are called :term:`annotation expressions <tspec:annotation expression>`.
An annotation expression is a :term:`tspec:type expression`, optionally surrounded by one or more
:term:`type qualifiers <tspec:type qualifier>` or by the :data:`~typing.Annotated` form.

For instance, in the following example::

    from typing import Annotated, ClassVar

    class A:
        x: ClassVar[Annotated[int, "meta"]]

The type hint of ``x`` is an annotation expression. The underlying type expression is :python:`int`. It is wrapped
by the :data:`~typing.ClassVar` type qualifier, and the :data:`~typing.Annotated` :term:`tspec:special form`.

The goal of this step is to:

- Unwrap the underlying :term:`tspec:type expression`.
- Keep track of the type qualifiers and annotated metadata.

To unwrap the type hint, use the :func:`~typing_inspection.introspection.inspect_annotation` function::

    >>> from typing_inspection.introspection import AnnotationSource, inspect_annotation
    >>> inspect_annotation(
    ...    ClassVar[Annotated[int, "meta"]],
    ...    annotation_source=AnnotationSource.CLASS,
    ... )
    ...
    InspectedAnnotation(type=int, qualifiers={"class_var"}, metadata=["meta"])

Note that depending on the annotation source, different type qualifiers can be (dis)allowed.
For instance, :class:`~typing.TypedDict` classes allow :data:`~typing.Required` and :data:`~typing.NotRequired`,
which are not allowed elsewhere (the allowed typed qualifiers are documented in the
:class:`~typing_inspection.introspection.AnnotationSource` enum class).

A :exc:`~typing_inspection.introspection.ForbiddenQualifier` exception is raised if an invalid qualifier is used. If you want
to allow all of them, use the :attr:`AnnotationSource.ANY <typing_inspection.introspection.AnnotationSource.ANY>` annotation
source.

.. admonition:: Parsing :pep:`695` type aliases

    In Python 3.12, the new :keyword:`python:type` statement can be used to define :ref:`type aliases <python:type-aliases>`.
    When a type alias is wrapped by the :data:`~typing.Annotated` form, the type alias' value will *not* be unpacked by Python
    at runtime. This means that while the following is technically valid::

        type MyInt = Annotated[int, "int_meta"]

        class A:
            x: Annotated[MyInt, "other_meta"]

    we need to parse the type alias during annotation inspection. This behavior can be controlled using the
    :paramref:`~typing_inspection.introspection.inspect_annotation.unpack_type_aliases` parameter::

        >>> inspect_annotation(
        ...     Annotated[MyInt, "other_meta"],
        ...     annotation_source=AnnotationSource.CLASS,
        ...     unpack_type_aliases="eager",  # This is the default
        ... )
        ...
        InspectedAnnotation(type=int, qualifiers={}, metadata=["int_meta", "other_meta"])

    Note that type aliases are lazily evaluated. During type alias inspection, any undefined symbol
    will raise a :exc:`NameError`. To prevent this from happening, you can use :python:`"keep"` to
    avoid expanding type aliases, or :python:`"lenient"` to fallback to :python:`"keep"` if the type
    alias contains an undefined symbol::

        >>> type BrokenType = Annotated[Undefined, ...]
        >>> type MyAlias = Annotated[BrokenType, "meta"]
        >>> inspect_annotation(
        ...     MyAlias,
        ...     annotation_source=AnnotationSource.CLASS,
        ...     unpack_type_aliases="lenient",
        ... )
        ...
        InspectedAnnotation(type=BrokenType, qualifiers={}, metadata=["meta"])

Inspecting the type expression
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With the qualifiers and :data:`~typing.Annotated` forms removed, we can now proceed to inspect
the type expression.

First of all, some simple typing :term:`special forms <tspec:special form>` can be checked::

    from typing_inspection.typing_objects import is_any, is_self

    type_expr = ...  # This would come from `InspectedAnnotation.type`

    if is_any(type_expr):
        ...  # Handle `typing.Any`

    if is_self(type_expr):
        ...  # Handle `typing.Self`

We will then use the :func:`typing.get_origin` function to fetch the origin of the type. Depending
on the type, the origin have different meanings::

    from typing_inspection.introspection import get_literal_values, is_union_origin
    from typing_inspection.typing_objects import is_annotated, is_literal

    origin = get_origin(type_expr)

    if is_union_origin(origin):
        # Handle `typing.Union` (or new `|` syntax)
        union_args = type_expr.__args__
        ...

    # You may also want to check for Annotated forms. While we unwrapped them
    # in step 2, `Annotated` can be used in parts of the annotation, e.g.
    # `list[Annotated[int, ...]]`:
    if is_annotated(origin):
        annotated_type = type_expr.__origin__  # not to be confused with the origin above
        metadata = type_expr.__metadata__

    if is_literal(origin):
        # Handle `typing.Literal`
        literal_values = get_literal_values(type_expr)


While :data:`~typing.Literal` values can be fetched using ``type_expr.__args__``, the
:func:`~typing_inspection.introspection.get_literal_values` function ensures :pep:`695` type aliases
are properly expanded.

Next, we will take care of the typing aliases deprecated by :pep:`585`. For instance,
:class:`typing.List` is deprecated and replaced by the built-in :class:`list` type. The origin
of an *unparameterized* deprecated type alias is the replacement type, so we will use this one::

    from typing_inspection.typing_objects import DEPRECATED_ALIASES

    # If `type_expr` is `typing.List`, `origin` is the built-in `list`.
    # We thus replace `type_expr` with `list`, and set `origin` to `None`
    # to emulate the same behavior if `type_expr` was `list` in the beginning:
    if origin is not None and type_expr in DEPRECATED_ALIASES:
        type_expr = origin
        origin = None

If a deprecated type alias is *parameterized*, the origin will point to the replacement type.

At this point, if ``origin`` is not :data:`None`, you can safely assume that ``type_expr`` is a
parameterized generic type::

    if origin is not None:
        handle_generic_type(type=origin, arguments=type_expr.__args__)
    else:
        handle_type(type=type_expr)
