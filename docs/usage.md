# Usage

The library is divided into two submodules:

- [`typing_inspection.typing_objects`][]: provides functions to check if a variable is a [`typing`][] object:
  ```python
  from typing_extensions import Union, get_origin

  from typing_inspection.typing_objects import is_union

  is_union(get_origin(Union[int, str]))  # True
  ```

    !!! note
        You might be tempted to use a simple identity check:

        ```pycon
        >>> get_origin(Union[int, str]) is typing.Union
        ```

        However, [`typing_extensions`][] might provide a different version of the [`typing`][] objects. Instead,
        the [`typing_objects`][typing_inspection.typing_objects] functions make sure to check against both variants,
        if they are different.

- [`typing_inspection.introspection`][]: provides high-level introspection functions, taking runtime edge cases
  into account.

## Inspecting annotations

If, as a library, you rely heavily on type hints, you may encounter subtle unexpected behaviors and performance
issues when inspecting annotations. As such, this section provides a recommended workflow to do so.

### Fetching type hints

The first step is to gather the type annotations from the object you want to inspect. The
[`typing.get_type_hints()`][typing.get_type_hints] function can be used to do so. If you want to make use of annotated
metadata, make sure to set the `include_extras` argument to `True`.

```pycon
>>> class A:
...    x: int
...    y: Annotated[int, ...]
...
>>> get_type_hints(A, include_extras=True)
{'x': int, 'y': Annotated[int, ...]}
```

!!! note
    Currently, `typing-inspection` does not provide any utility to fetch (and evaluate) type annotations. The current
    [`typing`][] utilities might contain subtle bugs across the different Python versions, so there is value in
    having similar functionality. It might be best to wait for [PEP 649](https://peps.python.org/pep-0649/) to be fully
    implemented first. In the meanwhile, the [`typing_extensions.get_type_hints()`][typing_extensions.get_type_hints]
    backport can be used.

### Unpacking metadata and qualifiers

The annotations fetched in the previous step are called [annotation expressions][annotation expression].
An annotation expression is a [type expression][], optionally surrounded by one or more [type qualifiers][type qualifier]
or by the [`Annotated`][typing.Annotated] form.

For instance, in the following example:

```python
from typing import Annotated, ClassVar

class A:
    x: ClassVar[Annotated[int, "meta"]]
```


The type hint of `x` is an annotation expression. The underlying type expression is `int`. It is wrapped
by the [`ClassVar`][typing.ClassVar] type qualifier, and the [`Annotated`][typing.Annotated] [special form][].

The goal of this step is to:

- Unwrap the underlying [type expression][].
- Keep track of the type qualifiers and annotated metadata.

To unwrap the type hint, use the [`inspect_annotation()`][typing_inspection.introspection.inspect_annotation] function:

```pycon
>>> from typing_inspection.introspection import AnnotationSource, inspect_annotation
>>> inspect_annotation(
...    ClassVar[Annotated[int, "meta"]],
...    annotation_source=AnnotationSource.CLASS,
... )
...
InspectedAnnotation(type=int, qualifiers={"class_var"}, metadata=["meta"])
```

Note that depending on the annotation source, different type qualifiers can be (dis)allowed.
For instance, [`TypedDict`][typing.TypedDict] classes allow [`Required`][typing.Required] and [`NotRequired`][typing.NotRequired],
which are not allowed elsewhere (the allowed typed qualifiers are documented in the
[`AnnotationSource`][typing_inspection.introspection.AnnotationSource] enum class).

A [ForbiddenQualifier][typing_inspection.introspection.ForbiddenQualifier] exception is raised if an invalid qualifier is used.
If you want to allow all of them, use the [`AnnotationSource.ANY`][typing_inspection.introspection.AnnotationSource.ANY] annotation
source.

The result of the [`inspect_annotation()`][typing_inspection.introspection.inspect_annotation] function contains the underlying
[type expression][], the qualifiers and the annotated metadata. Note that some qualifiers are allowed to be used without any
type expression. In this case, the type should be inferred from the assigned value:

```python
class A:
    x: Annotated[Final, 'meta'] = 1  # type of x should be inferred to `int`.
```

In this case, the [`InspectedAnnotation.type`][typing_inspection.introspection.InspectedAnnotation.type] attribute is set
to the [`INFERRED`][typing_inspection.introspection.INFERRED] sentinel value, so you should check for this sentinel value
before doing any processing on the type:

```python
from typing_inspection.introspection import INFERRED, AnnotationSource, inspect_annotation

inspected_annotation = inspect_annotation(
    Annotated[Final, 'meta'],
    annotation_source=AnnotationSource.CLASS,
)

if inspected_annotation.type is INFERRED:
    ann_type = type(assigned_value)  # assigned_value would come from the class
else:
    ann_type = inspected_annotation.type
```

!!! note "Parsing [PEP 695](https://peps.python.org/pep-0695/) type aliases"
    In Python 3.12, the new [type][] statement can be used to define [type aliases][type-aliases].
    When a type alias is wrapped by the [`Annotated`][typing.Annotated] form, the type alias' value will *not* be unpacked by Python
    at runtime. This means that while the following is technically valid:

    ```python
    type MyInt = Annotated[int, "int_meta"]

    class A:
        x: Annotated[MyInt, "other_meta"]
    ```

    it might be necessary to parse the type alias during annotation inspection. This behavior can be controlled using the
    `unpack_type_aliases` parameter:

    ```pycon
    >>> inspect_annotation(
    ...     Annotated[MyInt, "other_meta"],
    ...     annotation_source=AnnotationSource.CLASS,
    ...     unpack_type_aliases="eager",
    ... )
    ...
    InspectedAnnotation(type=int, qualifiers={}, metadata=["int_meta", "other_meta"])
    ```

    Whether you should unpack type aliases depends on your use case. If the annotated metadata present in the type alias
    is *only* meant to be applied on the annotated type (and not the attribute that will be type hinted), you probably
    need to keep type aliases as is, and possibly error later if invalid metadata is found when inspecting the type alias.

    Note that type aliases are lazily evaluated. During type alias inspection, any undefined symbol
    will raise a [`NameError`][]. To prevent this from happening, you can use `'skip'` to avoid expanding
    type aliases (the default), or `'lenient'` to fallback to `'skip'` if the type alias contains an undefined
    symbol:

    ```pycon
    >>> type BrokenType = Annotated[Undefined, ...]
    >>> type MyAlias = Annotated[BrokenType, "meta"]
    >>> inspect_annotation(
    ...     MyAlias,
    ...     annotation_source=AnnotationSource.CLASS,
    ...     unpack_type_aliases="lenient",
    ... )
    ...
    InspectedAnnotation(type=BrokenType, qualifiers={}, metadata=["meta"])
    ```

### Inspecting the type expression

With the qualifiers and [`Annotated`][typing.Annotated] forms removed, we can now proceed to inspect
the type expression.

First of all, some simple typing [special forms][special form] can be checked:

```python
from typing_inspection.typing_objects import is_any, is_self

# This would come from `InspectedAnnotation.type`, after checking for `INFERRED`:
type_expr = ...

if is_any(type_expr):
    ...  # Handle `typing.Any`

if is_self(type_expr):
    ...  # Handle `typing.Self`
```

We will then use the [`typing.get_origin()`][typing.get_origin] function to fetch the origin of the type. Depending
on the type, the origin has different meanings:

```python
from typing_inspection.introspection import get_literal_values, is_union_origin
from typing_inspection.typing_objects import is_annotated, is_literal

origin = get_origin(type_expr)

if is_union_origin(origin):
    # Handle `typing.Union` (or the new `|` syntax)
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
```

While [`Literal`][typing.Literal] values can be retrieved using `type_expr.__args__`, the
[`get_literal_values()`][typing_inspection.introspection.get_literal_values] function ensures
[PEP 695](https://peps.python.org/pep-0695/) type aliases are properly expanded.

Next, we will take care of the typing aliases deprecated by [PEP 585](https://peps.python.org/pep-0585/).
For instance, [`typing.List`][] is deprecated and replaced by the built-in [`list`][] type. In this case,
the origin of an *unparameterized* deprecated type alias is the replacement type, so we will use this one:

```python
from typing_inspection.typing_objects import DEPRECATED_ALIASES

# If `type_expr` is `typing.List`, `origin` is the built-in `list`.
# We thus replace `type_expr` with `list`, and set `origin` to `None`
# to emulate the same behavior if `type_expr` was `list` in the beginning:
if origin is not None and type_expr in DEPRECATED_ALIASES:
    type_expr = origin
    origin = None
```

At this point, if `origin` is not `None`, you can safely assume that `type_expr` is a parameterized generic type.
You can then define your own logic to handle the type expression, and have different code paths if you are
dealing with a parameterized type (e.g. `list[int]`) or a "bare" type:

```python
if origin is not None:
    handle_generic_type(type=origin, arguments=type_expr.__args__)
else:
    handle_type(type=type_expr)
```

!!! note
    If a deprecated type alias is *parameterized* (e.g. `typing.List[int]`), the origin will be the
    replacement type (e.g. `list`), and not the deprecated alias (e.g. `typing.List`). This means
    that handling `typing.List[int]` or `list` should be equivalent.
