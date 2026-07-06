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
        if not book.cover:
            cover_images.append(None)
            continue

        image = _download_cover(book.cover, f"book_cover_{index}", index)
        cover_images.append(image)

    return cover_images


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
