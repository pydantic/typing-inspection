## v0.4.2 (2025-10-01)

- Add `typing_objects.is_noextraitems()` by @Viicos in [#47](https://github.com/pydantic/typing-inspection/pull/47)

## v0.4.1 (2025-05-21)

- Fix compatibility with latest Python 3.14 release by @Viicos in [#37](https://github.com/pydantic/typing-inspection/pull/37)
- Add `typing_objects.is_forwardref()` by @Viicos in [#38](https://github.com/pydantic/typing-inspection/pull/38)
- Fix implementation of `is_union_origin()` by @Viicos in [#40](https://github.com/pydantic/typing-inspection/pull/40)
- Add SPDX license identifier by @cdce8p in [#42](https://github.com/pydantic/typing-inspection/pull/42)
- Use `list` as a type hint for `InspectedAnnotation.metadata` by @Viicos in [#43](https://github.com/pydantic/typing-inspection/pull/43)

## v0.4.0 (2025-02-25)

- Add support for `dataclasses.InitVar` as a type qualifier by @Viicos in [#31](https://github.com/pydantic/typing-inspection/pull/31)
  A new `DATACLASS` annotation source is added.
- Add explicit annotation for `ForbiddenQualifier` exception by @Viicos in [#30](https://github.com/pydantic/typing-inspection/pull/30)

## v0.3.1 (2025-02-24)

- Allow unhashable items in `Literal` forms by @Viicos in [#28](https://github.com/pydantic/typing-inspection/pull/28)

## v0.3.0 (2025-02-24)

- Handle bare `ClassVar` type qualifiers, rename `INFERRED` sentinel by @Viicos in [#26](https://github.com/pydantic/typing-inspection/pull/26)
  While currently not explicitly allowed by the typing specification, `ClassVar` is allowed as a bare type qualifier.
  Unlike `Final`, the actual type doesn't have to be inferred from the assignment (e.g. one can use `Any`).
  For this reason, the `INFERRED` sentinel was renamed to `UNKNOWN`.

## v0.2.0 (2025-02-23)

- Add `typing_objects.is_deprecated()` by @Viicos in [#24](https://github.com/pydantic/typing-inspection/pull/24)
- Add missing positional only parameter markers in `typing_objects` stub file by @Viicos in [#23](https://github.com/pydantic/typing-inspection/pull/23)
- Add project URLs by @Viicos in [#22](https://github.com/pydantic/typing-inspection/pull/22)

## v0.1.0 (2025-02-22)

Initial release.
