"""
Run generated output files and show what they do
"""

import ast
import importlib.util
import subprocess
import sys
import json
from pathlib import Path


def classify_file(content: str) -> str:
    try:
        tree = ast.parse(content)
        imports = []
        funcs = []
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.FunctionDef):
                funcs.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        parts = []
        if imports:
            parts.append(f"imports: {', '.join(imports[:5])}")
        if funcs:
            parts.append(f"defines: {', '.join(funcs[:5])}")
        if classes:
            parts.append(f"classes: {', '.join(classes[:5])}")
        return "; ".join(parts) if parts else "script"
    except SyntaxError as e:
        return f"SYNTAX ERROR: {e.msg}"


def run_file(filepath: Path):
    content = filepath.read_text(encoding="utf-8")
    if not content.strip():
        return {"status": "EMPTY", "output": ""}

    if not content.strip().startswith(("import", "from", "def ", "class ", "@", "#!", "print", "if ")):
        try:
            json.loads(content)
            return {"status": "JSON", "output": f"Valid JSON: {content[:200]}"}
        except json.JSONDecodeError:
            pass

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return {"status": "SYNTAX ERROR", "output": str(e)}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, 'attr', None) == 'run':
            return {"status": "WEB APP", "output": "Contains app.run() - starts a web server. Install dependencies then run it directly."}

    result = subprocess.run(
        [sys.executable, "-c", content],
        capture_output=True, text=True, timeout=5
    )
    if result.returncode == 0:
        stdout = result.stdout.strip() or "(no output, loaded without errors)"
        return {"status": "RAN OK", "output": stdout[:500]}
    else:
        stderr = result.stderr.strip()[:500]
        return {"status": "RUNTIME ERROR", "output": stderr}


def main():
    out_dir = Path(__file__).parent / "output"
    if not out_dir.exists():
        print(f"Output directory not found: {out_dir}")
        return

    py_files = sorted(out_dir.glob("*.py"))
    if not py_files:
        print("No .py files found in output/")
        return

    print("=" * 60)
    print("RUNNING GENERATED FILES")
    print("=" * 60)

    for f in py_files:
        if f.name.startswith("."):
            continue
        content = f.read_text(encoding="utf-8")
        classification = classify_file(content)
        rel = f.relative_to(out_dir.parent)

        print(f"\n{'-' * 60}")
        print(f"FILE: {rel}")
        print(f"SIZE: {len(content)} bytes")
        print(f"TYPE: {classification}")
        print(f"{'-' * 60}")
        print(content.rstrip()[:300])
        if len(content) > 300:
            print("  ... (truncated)")

        result = run_file(f)
        status = result["status"]
        output = result["output"]
        status_icon = {"RAN OK": "OK", "JSON": "OK", "EMPTY": "--"}.get(status, "ERROR")
        print(f"\n  [{status_icon}] {status}")
        if output:
            for line in output.splitlines()[:5]:
                print(f"    | {line}")

    print(f"\n{'=' * 60}")
    print("DONE")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
