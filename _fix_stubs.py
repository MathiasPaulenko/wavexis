"""Fix docstrings for single-line stub methods in test files by splitting lines."""

import re
from pathlib import Path


def make_func_docstring(name: str) -> str:
    desc = name.replace("_", " ")
    return f'"""{desc.capitalize()}."""'


def fix_stubs(path: Path) -> int:
    source = path.read_text(encoding="utf-8")
    lines = source.split("\n")
    new_lines: list[str] = []
    count = 0

    # Pattern: indented `async def name(...): ...` or `def name(...): ...`
    stub_pattern = re.compile(r'^(\s+)(async )?def (\w+)\(.*\):\s*\.\.\.\s*$')

    for line in lines:
        m = stub_pattern.match(line)
        if m:
            indent = m.group(1)
            async_kw = m.group(2) or ""
            func_name = m.group(3)
            # Replace `: ...` with `:` and add docstring on next line
            def_part = line.rstrip().rstrip(".").rstrip().rstrip(":").rstrip()
            new_lines.append(def_part + ":")
            body_indent = indent + "    "
            new_lines.append(body_indent + make_func_docstring(func_name))
            count += 1
        else:
            new_lines.append(line)

    if count > 0:
        path.write_text("\n".join(new_lines), encoding="utf-8")
    return count


files = [
    Path("tests/unit/test_manager.py"),
    Path("tests/unit/test_backend_manager.py"),
]

for f in files:
    count = fix_stubs(f)
    print(f"  {f}: +{count} docstrings")
