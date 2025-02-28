# Temporary hack to discard the actual py file and only use the stub file.
# See https://github.com/mkdocstrings/mkdocstrings/issues/737.
from pathlib import Path

path = Path(__file__).parents[2] / 'src' / 'typing_inspection'


def on_startup(*args: object, **kwargs: object) -> None:
    path.joinpath('typing_objects.py').rename(path / 'typing_objects._py')


def on_shutdown() -> None:
    path.joinpath('typing_objects._py').rename(path / 'typing_objects.py')
