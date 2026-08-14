"""Strip emoji glyphs from source files WITHOUT changing indentation/whitespace."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "vendor",
    ".next",
    "__pycache__",
    "out",
}

# Replace common status marks first (multi-codepoint sequences before singles)
REPLACEMENTS = [
    ("⚠️", "[WARN]"),
    ("⚠", "[WARN]"),
    ("ℹ️", "[INFO]"),
    ("ℹ", "[INFO]"),
    ("✅", "[OK]"),
    ("❌", "[ERR]"),
    ("💥", "[ERR]"),
    ("📊", "[INFO]"),
    ("🚀", ""),
    ("🎉", "[OK]"),
    ("✨", ""),
    ("💡", ""),
    ("📝", ""),
    ("⭐", ""),
    ("🔥", ""),
    ("⚙️", ""),
    ("⚙", ""),
    ("🏷️", ""),
    ("🏷", ""),
    ("🗄️", ""),
    ("🗄", ""),
    ("🔴", ""),
    ("🟢", ""),
    ("🟡", ""),
    ("⬜", "[ ]"),
    ("🔄", "[~]"),
    ("⏸", "[=]"),
]

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "\U0000FE0F"
    "\U0000200D"
    "]+"
)


def scrub(text: str) -> str:
    for src, dst in REPLACEMENTS:
        text = text.replace(src, dst)
    return EMOJI_RE.sub("", text)


def main() -> None:
    changed = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".ps1", ".md"}:
            continue
        if path.name == "strip_emojis.py":
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        updated = scrub(original)
        if updated != original:
            # preserve original newline style
            path.write_text(updated, encoding="utf-8", newline="")
            changed.append(str(path.relative_to(ROOT)))
    print(f"updated {len(changed)} files")
    for name in changed:
        print(name)


if __name__ == "__main__":
    main()
