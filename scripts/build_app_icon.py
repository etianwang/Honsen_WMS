"""从 logo.png 生成 Windows 多尺寸 logo.ico（供 PyInstaller 使用）。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PNG = ROOT / "logo.png"
ICO = ROOT / "logo.ico"

SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]


def main() -> None:
    if not PNG.is_file():
        raise SystemExit(f"未找到 {PNG}")

    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("请先安装 Pillow：python -m pip install pillow") from exc

    src = Image.open(PNG).convert("RGBA")
    pixels = src.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = pixels[x, y]
            if r > 235 and g > 235 and b > 235:
                pixels[x, y] = (r, g, b, 0)

    base = src.resize((256, 256), Image.Resampling.LANCZOS)
    layers = [base.resize(size, Image.Resampling.LANCZOS) for size in SIZES]
    layers[0].save(
        ICO,
        format="ICO",
        append_images=layers[1:],
        sizes=[(layer.width, layer.height) for layer in layers],
    )
    print(f"已生成 {ICO}（{len(SIZES)} 个尺寸）")


if __name__ == "__main__":
    main()
