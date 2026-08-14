import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).parent / "assets"

WATERMARK_PATHS = {
    "fashion": ASSETS_DIR / "watermark-fashion.jpg",
    "hair": ASSETS_DIR / "watermark-hair.jpg",
}


def _cutout_mark(mark_path: Path) -> Image.Image:
    """The source files are the circular brand badge inscribed in a solid
    black square. A luminosity-based cutout doesn't work uniformly across
    both marks — one is light text on a dark badge, the other dark text on
    a light badge — so instead mask to the circle itself (supersampled for
    a clean anti-aliased edge), keeping the whole badge, disc and lettering
    alike, at one consistent opacity."""
    with Image.open(mark_path) as src:
        rgb = src.convert("RGB")
        w, h = rgb.size
        supersample = 4
        big_w, big_h = w * supersample, h * supersample
        mask_big = Image.new("L", (big_w, big_h), 0)
        diameter = int(min(big_w, big_h) * 0.97)
        cx, cy = big_w // 2, big_h // 2
        ImageDraw.Draw(mask_big).ellipse(
            [cx - diameter // 2, cy - diameter // 2, cx + diameter // 2, cy + diameter // 2],
            fill=255,
        )
        mask = mask_big.resize((w, h), Image.LANCZOS)

        mark = rgb.convert("RGBA")
        mark.putalpha(mask)
        return mark


def _tile_layer(width: int, height: int, watermark: str) -> Image.Image:
    """Builds the actual repeating-diagonal watermark pattern as its own
    transparent RGBA layer, sized to (width, height). A single corner stamp
    is trivial to crop out of a screenshot; this tiled pattern isn't, while
    staying light enough not to spoil the shot. Shared by the photo path
    (composited directly) and the video path (saved as a PNG overlay)."""
    mark_path = WATERMARK_PATHS[watermark]

    tile_w = max(int(width * 0.16), 60)
    mark = _cutout_mark(mark_path)
    ratio = tile_w / mark.width
    mark = mark.resize((tile_w, max(int(mark.height * ratio), 1)), Image.LANCZOS)

    alpha = mark.split()[3].point(lambda p: int(p * 0.4))
    mark.putalpha(alpha)
    mark = mark.rotate(30, expand=True, resample=Image.BICUBIC)

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    step_x = mark.width + tile_w // 2
    step_y = mark.height + tile_w // 2
    row = 0
    y = -mark.height
    while y < height + mark.height:
        offset = 0 if row % 2 == 0 else step_x // 2
        x = -mark.width
        while x < width + mark.width:
            layer.paste(mark, (x + offset, y), mark)
            x += step_x
        y += step_y
        row += 1

    return layer


def apply_watermark(image_bytes: bytes, watermark: str) -> bytes:
    """Composites the tiled brand-mark pattern onto a photo."""
    base = Image.open(BytesIO(image_bytes)).convert("RGBA")
    layer = _tile_layer(base.width, base.height, watermark)
    watermarked = Image.alpha_composite(base, layer).convert("RGB")

    out = BytesIO()
    watermarked.save(out, format="JPEG", quality=90)
    return out.getvalue()


def apply_watermark_to_video(video_bytes: bytes, watermark: str) -> bytes:
    """Same tiled pattern, overlaid on every frame via ffmpeg. Requires
    ffmpeg/ffprobe on PATH (see backend/railpack.json — Railway installs it
    as an apt package at deploy time; not available in older deployments
    that predate that config)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        src_path = tmp / "input"
        overlay_path = tmp / "overlay.png"
        out_path = tmp / "output.mp4"

        src_path.write_bytes(video_bytes)

        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0", str(src_path),
            ],
            capture_output=True, text=True, check=True,
        )
        width_str, height_str = probe.stdout.strip().split("x")
        width, height = int(width_str), int(height_str)

        layer = _tile_layer(width, height, watermark)
        layer.save(overlay_path, format="PNG")

        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src_path), "-i", str(overlay_path),
                "-filter_complex", "overlay=0:0",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "copy",
                str(out_path),
            ],
            capture_output=True, check=True,
        )

        return out_path.read_bytes()
