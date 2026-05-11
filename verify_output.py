"""
Output Verifier - Checks generated project quality, syntax, and structure
"""

import ast
import sys
import json
from pathlib import Path


def check_python_syntax(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    try:
        ast.parse(content)
        loc = len(content.splitlines())
        return {"status": "PASS", "lines": loc, "bytes": len(content), "error": None}
    except SyntaxError as e:
        return {"status": "FAIL", "lines": 0, "bytes": len(content), "error": str(e)}


def check_sql(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    loc = len(content.splitlines())
    keywords = ["CREATE", "TABLE", "INSERT", "SELECT", "INDEX"]
    found = [kw for kw in keywords if kw in content.upper()]
    return {
        "status": "PASS" if found else "WARN",
        "lines": loc,
        "bytes": len(content),
        "sql_keywords_found": found
    }


def check_text(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    loc = len(content.splitlines())
    return {"status": "PASS", "lines": loc, "bytes": len(content), "preview": content[:100]}


CHECKS = {
    ".py": check_python_syntax,
    ".sql": check_sql,
    ".md": check_text,
    ".txt": check_text,
    ".json": check_text,
    ".html": check_text,
    ".css": check_text,
    ".js": check_text,
    ".jsx": check_text,
    ".tsx": check_text,
    ".yaml": check_text,
    ".yml": check_text,
    ".cfg": check_text,
    ".ini": check_text,
    ".toml": check_text,
}


def verify_project(output_dir: str) -> dict:
    base = Path(output_dir)
    if not base.exists():
        return {"error": f"Output directory not found: {output_dir}"}

    results = {}
    all_files = sorted(base.rglob("*"))
    total_bytes = 0
    passed = 0
    failed = 0
    warned = 0

    for f in all_files:
        if not f.is_file() or f.name.startswith("."):
            continue
        if ".locks" in f.parts:
            continue

        ext = f.suffix.lower()
        checker = CHECKS.get(ext)
        if checker:
            try:
                result = checker(f)
                result["file"] = str(f.relative_to(base))
                results[str(f.relative_to(base))] = result
                total_bytes += result.get("bytes", 0)
                if result["status"] == "PASS":
                    passed += 1
                elif result["status"] == "FAIL":
                    failed += 1
                else:
                    warned += 1
            except Exception as e:
                results[f.name] = {"status": "ERROR", "error": str(e)}
                failed += 1
        else:
            size = f.stat().st_size
            total_bytes += size
            results[f.name] = {"status": "SKIP", "reason": f"Unknown extension {ext}", "bytes": size}

    return {
        "files_checked": len(results),
        "passed": passed,
        "failed": failed,
        "warned": warned,
        "total_bytes": total_bytes,
        "details": results
    }


def print_report(report: dict):
    print("\n" + "=" * 60)
    print("PROJECT VERIFICATION REPORT")
    print("=" * 60)
    if "error" in report:
        print(f"ERROR: {report['error']}")
        return

    print(f"Files checked: {report['files_checked']}")
    print(f"Total size:   {report['total_bytes']} bytes")
    print(f"Passed:       {report['passed']}")
    print(f"Failed:       {report['failed']}")
    if report['warned']:
        print(f"Warnings:     {report['warned']}")
    print("-" * 60)

    for fname, detail in report["details"].items():
        icon = "[OK]" if detail["status"] == "PASS" else "[FAIL]" if detail["status"] == "FAIL" else "[WARN]" if detail["status"] == "WARN" else "[SKIP]"
        size_str = f"{detail.get('bytes', 0)}B"
        lines_str = f"{detail.get('lines', '?')} lines" if 'lines' in detail else ""
        error_str = f" - {detail.get('error', '')}" if detail.get('error') else ""
        print(f"  {icon} {fname} ({size_str}, {lines_str}){error_str}")

    print("=" * 60)

    if report["failed"] == 0:
        print("SUMMARY: All files pass validation.")
    else:
        print(f"SUMMARY: {report['failed']} file(s) have errors that need fixing.")
    print()


if __name__ == "__main__":
    output_dir = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "output")
    report = verify_project(output_dir)
    print_report(report)
