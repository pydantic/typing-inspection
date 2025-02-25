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
