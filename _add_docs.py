"""Add Google-style docstrings to test files using AST body positions."""

import ast
from pathlib import Path


def make_module_docstring(path: Path) -> str:
    name = path.stem
    if path.parent.name == "unit":
        return f"Unit tests for {name.replace('test_', '')}."
    elif path.parent.name == "integration":
        return f"Integration tests for {name.replace('test_', '')}."
    return f"Tests for {name.replace('test_', '')}."


def make_class_docstring(name: str) -> str:
    clean = name.replace("Test", "").replace("_", " ")
    return f'"""Test suite for {clean.lower()}."""'


def make_func_docstring(name: str) -> str:
    if name.startswith("test_"):
        desc = name[5:].replace("_", " ")
        if "raises" in desc or "missing" in desc or "invalid" in desc:
            return f'"""Test that {desc} raises an appropriate error."""'
        if "lifecycle" in desc:
            return '"""Test the action lifecycle (launch, execute, close)."""'
        if "no_url" in desc or "skips" in desc:
            return '"""Test that navigation is skipped when no URL is provided."""'
        return f'"""Test {desc}."""'
    if name == "_make_backend":
        return '"""Create a mock backend for testing.\n\n    Returns:\n        A MagicMock backend instance.\n    """'
    if name == "wrapper":
        return '"""Wrap a function for testing."""'
    if name == "setup_method":
        return '"""Set up test fixtures before each test method."""'
    if name == "teardown_method":
        return '"""Clean up after each test method."""'
    if name == "_run":
        return '"""Execute the test action."""'
    desc = name.replace("_", " ")
    return f'"""{desc.capitalize()}."""'


def add_docstrings_to_file(path: Path) -> int:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0

    lines = source.split("\n")
    insertions: list[tuple[int, str]] = []

    # Module docstring
    if not ast.get_docstring(tree):
        mod_doc = make_module_docstring(path)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                insert_idx = i
                break
        insertions.append((insert_idx, f'"""{mod_doc}"""'))

    # Classes and functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not ast.get_docstring(node):
                if isinstance(node, ast.ClassDef):
                    doc = make_class_docstring(node.name)
                else:
                    doc = make_func_docstring(node.name)

                # body[0].lineno is 1-indexed line of first body statement
                body_start = node.body[0].lineno
                insert_idx = body_start - 1  # 0-indexed

                # Get indentation from the body's first line
                body_line = lines[insert_idx]
                indent = len(body_line) - len(body_line.lstrip())
                indent_str = " " * indent

                doc_lines = doc.split("\n")
                if len(doc_lines) == 1:
                    doc_text = indent_str + doc_lines[0]
                else:
                    doc_parts = [indent_str + doc_lines[0]]
                    for dl in doc_lines[1:]:
                        if dl.strip():
                            doc_parts.append(indent_str + dl)
                        else:
                            doc_parts.append(dl)
                    doc_text = "\n".join(doc_parts)

                insertions.append((insert_idx, doc_text))

    if not insertions:
        return 0

    # Sort by line index in reverse order
    insertions.sort(key=lambda x: x[0], reverse=True)

    for line_idx, text in insertions:
        lines.insert(line_idx, text)

    path.write_text("\n".join(lines), encoding="utf-8")
    return len(insertions)


def main():
    total = 0
    for root in [Path("tests")]:
        for pyfile in root.rglob("*.py"):
            if pyfile.name == "__init__.py":
                source = pyfile.read_text(encoding="utf-8")
                try:
                    tree = ast.parse(source)
                except SyntaxError:
                    continue
                if not ast.get_docstring(tree) and source.strip():
                    pyfile.write_text(
                        f'"""{pyfile.stem} package."""\n\n{source}',
                        encoding="utf-8",
                    )
                    total += 1
                continue

            count = add_docstrings_to_file(pyfile)
            if count > 0:
                print(f"  {pyfile}: +{count} docstrings")
                total += count

    print(f"\nTotal docstrings added: {total}")


if __name__ == "__main__":
    main()
