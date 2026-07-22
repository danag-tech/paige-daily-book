import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import requests


COVER_TIMEOUT = 10
MAX_COVERS = 3
COVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Referer": "https://book.douban.com/",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def download_cover_images(books: list) -> list[dict | None]:
    cover_images: list[dict | None] = []

    for index, book in enumerate(books[:MAX_COVERS], start=1):
        title = str(getattr(book, "title", "") or "书籍推荐")
        author = str(getattr(book, "author", "") or "Paige Book Daily")
        cover_url = str(getattr(book, "cover", "") or "").strip()
        image = _download_cover(cover_url, f"book_cover_{index}", index) if cover_url else None
        cover_images.append(image or _build_placeholder_cover(title, author, f"book_cover_{index}"))

    return cover_images


def build_placeholder_cover_png(title: str, author: str) -> bytes:
    """Generate a compact PNG cover for books without a usable real cover."""
    width, height = 420, 630
    image = Image.new("RGB", (width, height), "#efe7da")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 28, width - 28, height - 28), radius=18, fill="#fffdf8", outline="#dccdb9", width=2)

    small_font = _load_font(18)
    title_font = _load_font(34, bold=True)
    author_font = _load_font(22)
    draw.text((width // 2, 76), "PAIGE BOOK DAILY", font=small_font, fill="#7a4f2c", anchor="ma")

    title_lines = _wrap_text(draw, title.strip() or "书籍推荐", title_font, 308, 5)
    title_y = 174
    for line in title_lines:
        draw.text((width // 2, title_y), line, font=title_font, fill="#23201c", anchor="ma")
        title_y += 48

    author_lines = _wrap_text(draw, author.strip() or "Paige Book Daily", author_font, 280, 2)
    author_y = 442
    for line in author_lines:
        draw.text((width // 2, author_y), line, font=author_font, fill="#71695f", anchor="ma")
        author_y += 32
    draw.line((126, 548, 294, 548), fill="#d4b895", width=2)

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _build_placeholder_cover(title: str, author: str, cid: str) -> dict:
    return {
        "cid": cid,
        "image_bytes": build_placeholder_cover_png(title, author),
        "maintype": "image",
        "subtype": "png",
    }


def _load_font(size: int, bold: bool = False):
    project_font = Path(__file__).resolve().parent / "assets" / "fonts" / "NotoSansSC-Regular.otf"
    candidates = [
        project_font,
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansSC-Bold.otf" if bold else "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for character in text:
        candidate = current + character
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = character
            if len(lines) == max_lines:
                break
        else:
            current = candidate
    if len(lines) < max_lines and current:
        lines.append(current)
    if len(lines) == max_lines and sum(len(line) for line in lines) < len(text):
        lines[-1] = lines[-1][:-1] + "…"
    return lines or ["书籍推荐"]


def _download_cover(url: str, cid: str, index: int) -> dict | None:
    try:
        response = requests.get(
            url,
            headers=COVER_HEADERS,
            timeout=COVER_TIMEOUT,
        )
    except requests.RequestException as exc:
        return None


    if response.status_code != 200:
        return None

    image_bytes = response.content
    if not image_bytes:
        return None

    subtype = _detect_image_subtype(response.headers.get("Content-Type", ""), image_bytes)
    if not subtype:
        return None

    return {
        "cid": cid,
        "image_bytes": image_bytes,
        "maintype": "image",
        "subtype": subtype,
    }


def _detect_image_subtype(content_type: str, image_bytes: bytes) -> str | None:
    if content_type.startswith("image/"):
        subtype = content_type.split("/", 1)[1].split(";", 1)[0].strip().lower()
        if subtype == "jpg":
            return "jpeg"
        if subtype:
            return subtype

    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return "gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "webp"
    return None
