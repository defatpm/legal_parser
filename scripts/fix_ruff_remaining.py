#!/usr/bin/env python3
"""
fix_ruff_remaining.py
====================
Quick-and-dirty patcher for the *remaining* Ruff lint violations that the
`--fix --unsafe-fixes` pass couldn’t auto‑resolve:

* **E402** – late import in `src/processors/metadata_extractor.py`
* **B018** – useless expression (`1 / 0`) in `tests/test_logging.py`
* **B017** – blind `pytest.raises(Exception)` in `tests/test_pdf_extractor.py`
* **E721** – `== SystemExit` comparisons in `tests/test_process_pdf.py`

Run **from the repository root**:

```bash
python scripts/fix_ruff_remaining.py
```

Afterwards, re‑run your hooks:

```bash
pre-commit run --all-files
```

If anything still shows up, you can tweak the regexes below or just add a
`# noqa` comment manually.
"""
from __future__ import annotations

import pathlib
import re
import sys
from collections.abc import Callable, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

FIXES: Sequence[tuple[pathlib.Path, Callable[[str], str]]] = [
    # 1) E402 — append noqa to the late import
    (
        REPO_ROOT / "src/processors/metadata_extractor.py",
        lambda txt: re.sub(
            r"^\s*import\s+textacy\.extract\s*$",
            "import textacy.extract  # noqa: E402",
            txt,
            flags=re.MULTILINE,
        ),
    ),
    # 2) B018 — replace `1 / 0` with an explicit raise (maintains traceback logic)
    (
        REPO_ROOT / "tests/test_logging.py",
        lambda txt: re.sub(
            r"^\s*1\s*/\s*0\s*$",
            "raise ZeroDivisionError()  # noqa: B018",
            txt,
            flags=re.MULTILINE,
        ),
    ),
    # 3) B017 — add noqa comment to generic Exception assertions (x2)
    (
        REPO_ROOT / "tests/test_pdf_extractor.py",
        lambda txt: re.sub(
            r"with pytest\.raises\(Exception\):",
            "with pytest.raises(Exception):  # noqa: B017",
            txt,
        ),
    ),
    # 4) E721 — turn `== SystemExit` into `is SystemExit` (x2)
    (
        REPO_ROOT / "tests/test_process_pdf.py",
        lambda txt: re.sub(
            r"==\s*SystemExit",
            "is SystemExit",
            txt,
        ),
    ),
]


def patch_file(path: pathlib.Path, transform: Callable[[str], str]) -> bool:
    """Apply *transform* and write back only if something changed."""
    if not path.exists():
        print(f"[WARN] {path.relative_to(REPO_ROOT)} does not exist, skipped.")
        return False
    original = path.read_text()
    patched = transform(original)
    if patched != original:
        path.write_text(patched)
        print(f"[FIXED] {path.relative_to(REPO_ROOT)}")
        return True
    return False


def main() -> None:
    changed_any = False
    for file_path, transformer in FIXES:
        changed_any |= patch_file(file_path, transformer)

    if not changed_any:
        print("Nothing patched — maybe you already fixed these issues.")
    else:
        print("\n✅ All patches applied. Re‑run `pre-commit run --all-files`.\n")


if __name__ == "__main__":
    sys.exit(main())
