from __future__ import annotations

import importlib.util
import inspect
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEST_DIR = ROOT / "tests"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    failures: list[str] = []
    passed = 0
    for test_file in sorted(TEST_DIR.glob("test_*.py")):
        module_name = f"tests_{test_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, test_file)
        if spec is None or spec.loader is None:
            failures.append(f"{test_file}: konnte nicht importiert werden")
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            failures.append(f"{test_file}: Importfehler\n{traceback.format_exc()}")
            continue
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            try:
                if "tmp_path" in inspect.signature(func).parameters:
                    temp = ROOT / ".test_tmp" / name
                    if temp.exists():
                        _delete_tree(temp)
                    temp.mkdir(parents=True, exist_ok=True)
                    func(temp)
                else:
                    func()
                passed += 1
                print(f"PASS {test_file.name}::{name}")
            except Exception:
                failures.append(f"{test_file.name}::{name}\n{traceback.format_exc()}")
    if failures:
        print("\nFEHLER:")
        for failure in failures:
            print(failure)
        print(f"\nERGEBNIS: {passed} bestanden, {len(failures)} fehlgeschlagen")
        return 1
    print(f"\nERGEBNIS: {passed} Tests bestanden")
    return 0


def _delete_tree(path: Path) -> None:
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file() or child.is_symlink():
            child.unlink()
        else:
            child.rmdir()
    path.rmdir()


if __name__ == "__main__":
    raise SystemExit(main())
