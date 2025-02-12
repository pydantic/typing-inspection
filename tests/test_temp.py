from typing import Any

from typing_inspection.typing_objects import is_any

def test_temp() -> None:
    assert is_any(Any)
