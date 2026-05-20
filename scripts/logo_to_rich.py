#!/usr/bin/env python3
"""Convert Kartoza logo PNG to Rich markup for terminal display.

Uses half-block characters (▀▄█) with fg/bg colors to achieve
2 vertical pixels per character cell, similar to catimg.

Usage:
    python scripts/logo_to_rich.py [width] > src/geotui/screens/logo_data.py
"""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("pip install Pillow", file=sys.stderr)
    sys.exit(1)


BG_THRESHOLD = 30  # Color distance threshold for "is background"

# Colors to treat as transparent (app bg + white areas in logo)
BG_COLORS = [
    (0x1A, 0x1A, 0x2E),  # App dark background
    (0xFF, 0xFF, 0xFF),  # White areas in SVG
]


def _is_bg(pixel: tuple) -> bool:
    """Check if a pixel is close to any background color.

    Args:
        pixel: RGBA or RGB pixel tuple.

    Returns:
        True if the pixel should be treated as transparent/background.
    """
    r, g, b = pixel[0], pixel[1], pixel[2]
    a = pixel[3] if len(pixel) > 3 else 255
    if a < 128:
        return True
    for bg in BG_COLORS:
        dr = abs(r - bg[0])
        dg = abs(g - bg[1])
        db = abs(b - bg[2])
        if (dr + dg + db) < BG_THRESHOLD:
            return True
    return False


def image_to_rich_lines(
    image_path: str, width: int = 40
) -> list[str]:
    """Convert an image to Rich markup lines using half-block chars.

    Each character cell encodes 2 vertical pixels using the upper
    half block (▀) with fg=top pixel, bg=bottom pixel.
    Pixels close to the app background color are rendered as spaces.

    Args:
        image_path: Path to the image file.
        width: Output width in terminal columns.

    Returns:
        List of Rich markup strings, one per line.
    """
    img = Image.open(image_path).convert("RGBA")

    # Scale to desired width, height must be even
    aspect = img.height / img.width
    height = int(width * aspect)
    if height % 2 != 0:
        height += 1
    img = img.resize((width, height), Image.LANCZOS)

    lines = []
    for y in range(0, height, 2):
        line = ""
        for x in range(width):
            top = img.getpixel((x, y))
            bot = img.getpixel((x, y + 1)) if y + 1 < height else (0, 0, 0, 0)

            top_bg = _is_bg(top)
            bot_bg = _is_bg(bot)

            if top_bg and bot_bg:
                line += " "
            elif top_bg:
                bc = f"#{bot[0]:02x}{bot[1]:02x}{bot[2]:02x}"
                line += f"[{bc}]▄[/{bc}]"
            elif bot_bg:
                fc = f"#{top[0]:02x}{top[1]:02x}{top[2]:02x}"
                line += f"[{fc}]▀[/{fc}]"
            else:
                fc = f"#{top[0]:02x}{top[1]:02x}{top[2]:02x}"
                bc = f"#{bot[0]:02x}{bot[1]:02x}{bot[2]:02x}"
                if fc == bc:
                    line += f"[{fc}]█[/{fc}]"
                else:
                    line += f"[{fc} on {bc}]▀[/{fc} on {bc}]"
        lines.append(line)

    return lines


def main() -> None:
    """Generate logo_data.py from the Kartoza logo."""
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    img_path = Path(__file__).parent.parent / "resources" / "kartoza-logo.png"

    if not img_path.exists():
        print(f"Image not found: {img_path}", file=sys.stderr)
        sys.exit(1)

    lines = image_to_rich_lines(str(img_path), width)

    print('"""Generated Kartoza logo in Rich markup."""')
    print("")
    print("LOGO_LINES = [")
    for line in lines:
        print(f"    {line!r},")
    print("]")
    print("")
    print('LOGO = "\\n".join(LOGO_LINES)')


if __name__ == "__main__":
    main()
