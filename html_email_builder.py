from html import escape
import re
from urllib.parse import quote, urlparse


def _book_value(book, name: str, default=""):
    if isinstance(book, dict):
        return book.get(name, default)
    return getattr(book, name, default)


def _normalize_isbn(value) -> str:
    isbn = re.sub(r"[\s-]+", "", str(value or "")).upper()
    if re.fullmatch(r"\d{9}[\dX]", isbn) or re.fullmatch(r"\d{13}", isbn):
        return isbn
    return ""


def _safe_https_url(value) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc:
        return url
    return ""


def _build_book_links(book) -> dict[str, str]:
    isbn = _normalize_isbn(_book_value(book, "isbn") or _book_value(book, "ISBN"))
    title = str(_book_value(book, "title", "") or "").strip()
    author = str(_book_value(book, "author", "") or "").strip()
    links = {}
    if isbn:
        links["douban"] = f"https://book.douban.com/isbn/{isbn}/"
    weread_url = _safe_https_url(_book_value(book, "weread_url"))
    links["weread"] = weread_url or (
        "https://weread.qq.com/web/search/books?keyword=" + quote(title, safe="")
    )
    search_term = isbn or f"{title} {author}".strip()
    links["jd"] = "https://search.jd.com/Search?keyword=" + quote(search_term, safe="") + "&enc=utf-8"
    return links


def _build_book_links_html(book) -> str:
    labels = (("douban", "豆瓣详情"), ("weread", "微信读书"), ("jd", "京东购买"))
    anchors = []
    for key, label in labels:
        url = _safe_https_url(_build_book_links(book).get(key))
        if url:
            anchors.append(
                f'<a href="{escape(url, quote=True)}" target="_blank" style="display:inline-block; margin:0 8px 6px 0; color:#6b4f3b; text-decoration:none; font-size:14px;">{escape(label)}</a>'
            )
    if not anchors:
        return ""
    return '<div style="margin:12px 0 0; line-height:1.6; word-break:break-word;">' + "".join(anchors) + "</div>"


def build_book_email_html(theme: str, books: list, summary: str, cover_cids: list[str | None] | None = None) -> str:
    safe_theme = escape(theme)
    normalized_cover_cids = cover_cids or []
    book_cards = "".join(
        _build_book_card(book, normalized_cover_cids[index] if index < len(normalized_cover_cids) else None)
        for index, book in enumerate(books)
    )
    return f"""<!doctype html>
<html>
<body style="margin:0; padding:0; background:#f6f6f6;">
  <div style="max-width:720px; margin:0 auto; padding:24px; font-family:Arial, sans-serif; line-height:1.7; color:#222; background:#ffffff;">
    <h1 style="font-size:24px; margin:0 0 16px;">今日荐书：{safe_theme}</h1>
    {book_cards}
  </div>
</body>
</html>"""


def _format_book_summary(summary: str | None) -> str:
    text = (summary or "暂无简介").strip() or "暂无简介"
    escaped_text = escape(text).replace("\n", "<br>")
    return f'<p style="margin:6px 0 0; color:#333; font-size:15px;">{escaped_text}</p>'


def _build_book_card(book, cover_cid: str | None) -> str:
    title = escape(book.title)
    author = escape(book.author)
    rating = escape(book.rating or "暂无")
    summary_html = _format_book_summary(book.summary)
    links_html = _build_book_links_html(book)
    if cover_cid:
        safe_cid = escape(cover_cid)
        cover_html = (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 20px;">'
            '<tr><td align="center" style="text-align:center;">'
            f'<img src="cid:{safe_cid}" alt="《{title}》封面" width="150" '
            'style="display:block; width:150px; max-width:42%; min-width:112px; height:auto; border-radius:4px; border:1px solid #ddd; margin:0 auto;">'
            '</td></tr></table>'
        )
    else:
        cover_html = (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 20px;">'
            '<tr><td align="center" style="text-align:center;">'
            '<table role="presentation" width="150" height="160" cellpadding="0" cellspacing="0" border="0" style="width:150px; max-width:42%; min-width:112px; border:1px solid #ddd; border-radius:4px; margin:0 auto;">'
            '<tr><td align="center" style="color:#777; font-size:14px;"></td></tr></table>'
            '</td></tr></table>'
        )
    return f"""
    <div style="border:1px solid #e5e5e5; border-radius:8px; padding:16px; margin:0 0 16px;">
      <div style="text-align:center;">
        <h3 style="font-size:18px; margin:0 0 10px;">《{title}》</h3>
        <p style="margin:0 0 6px; color:#444;">作者：{author}</p>
        <p style="margin:0; color:#444;">评分：{rating}</p>
        {cover_html}
      </div>
      <div style="text-align:left;">
        <p style="margin:0 0 6px; color:#444; font-weight:bold;">简介：</p>
        {summary_html}
        {links_html}
      </div>
    </div>
    """
