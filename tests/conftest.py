from __future__ import annotations

import importlib.util
import inspect
import re
import secrets
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path
from types import FunctionType, ModuleType

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook


def _extract_source_code_from_function(function: FunctionType) -> str:
    if function.__code__.co_argcount:
        raise RuntimeError(f'function {function.__qualname__} cannot have any arguments')

    code_lines = ''
    body_started = False
    for line in textwrap.dedent(inspect.getsource(function)).split('\n'):
        if line.startswith('def '):
            body_started = True
            continue
        elif body_started:
            code_lines += f'{line}\n'

    return textwrap.dedent(code_lines)


def _create_module_file(code: str, tmp_path: Path, name: str) -> tuple[str, str]:
    # Max path length in Windows is 260. Leaving some buffer here
    max_name_len = 240 - len(str(tmp_path))
    # Windows does not allow these characters in paths. Linux bans slashes only.
    sanitized_name = re.sub('[' + re.escape('<>:"/\\|?*') + ']', '-', name)[:max_name_len]
    name = f'{sanitized_name}_{secrets.token_hex(5)}'
    path = tmp_path / f'{name}.py'
    path.write_text(code)
    return name, str(path)


@pytest.fixture
def create_module(
    tmp_path: Path, request: pytest.FixtureRequest
) -> Callable[[FunctionType | str, bool, str | None], ModuleType]:
    def run(
        source_code_or_function: FunctionType | str,
        rewrite_assertions: bool = True,
        module_name_prefix: str | None = None,
    ) -> ModuleType:
        """
        Create module object, execute it and return
        Can be used as a decorator of the function from the source code of which the module will be constructed

        :param source_code_or_function string or function with body as a source code for created module
        :param rewrite_assertions: whether to rewrite assertions in module or not
        :param module_name_prefix: string prefix to use in the name of the module, does not affect the name of the file.

        """
        if isinstance(source_code_or_function, FunctionType):
            source_code = _extract_source_code_from_function(source_code_or_function)
        else:
            source_code = source_code_or_function

        module_name, filename = _create_module_file(source_code, tmp_path, request.node.name)  # pyright: ignore
        if module_name_prefix:
            module_name = module_name_prefix + module_name

        if rewrite_assertions:
            loader = AssertionRewritingHook(config=request.config)
            loader.mark_rewrite(module_name)
        else:
            loader = None

        spec = importlib.util.spec_from_file_location(module_name, filename, loader=loader)
        sys.modules[module_name] = module = importlib.util.module_from_spec(spec)  # pyright: ignore[reportArgumentType]
        spec.loader.exec_module(module)  # pyright: ignore[reportOptionalMemberAccess]
        return module

    return run
