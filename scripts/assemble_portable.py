"""Assemble portable dist folder + zip (exe only; system WebView2 required)."""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SPEC = ROOT / "desktop" / "honsen_wms.spec"


def main() -> None:
    text = SPEC.read_text(encoding="utf-8")
    match = re.search(r'name\s*=\s*"([^"]+)"', text)
    if not match:
        raise SystemExit(f"exe name not found in {SPEC}")

    exe_name = f"{match.group(1)}.exe"
    exe_path = DIST / exe_name
    if not exe_path.is_file():
        raise SystemExit(f"Missing built exe: {exe_path}")

    portable_name = f"{exe_path.stem}_portable"
    portable = DIST / portable_name
    if portable.exists():
        shutil.rmtree(portable)
    portable.mkdir(parents=True)

    shutil.copy2(exe_path, portable / exe_name)
    (portable / "db").mkdir()
    (portable / "README.txt").write_text(
        "Honsen WMS Sync Edition - Portable Package\n\n"
        "1. Unzip the whole folder before running.\n"
        "2. Requires Microsoft Edge WebView2 Runtime (system install).\n"
        "3. First run creates db/ and webview_data/ beside the exe.\n"
        "4. Default user: Honsen_Admin\n"
        "5. Default password: 66778899HONSEN\n",
        encoding="utf-8",
    )

    zip_path = DIST / f"{portable_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in portable.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(DIST).as_posix())

    print(f"==> Exe: {exe_path}")
    print(f"==> Portable: {portable}")
    print(f"==> Zip: {zip_path} ({zip_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
