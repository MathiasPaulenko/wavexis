import ast
import os

issues = []

for root, _dirs, files in os.walk("tests"):
    for f in files:
        if not f.endswith(".py"):
            continue
        path = os.path.join(root, f)
        with open(path, encoding="utf-8") as fh:
            try:
                source = fh.read()
                tree = ast.parse(source)
            except SyntaxError:
                issues.append(f"{path}: SYNTAX ERROR")
                continue

        if not ast.get_docstring(tree):
            issues.append(f"{path}: missing module docstring")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    lineno = node.lineno
                    name = node.name
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    issues.append(f"{path}:{lineno}: {kind} '{name}' missing docstring")

for issue in issues:
    print(issue)
print(f"\nTotal issues: {len(issues)}")
