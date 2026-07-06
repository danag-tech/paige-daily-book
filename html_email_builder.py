from html import escape


def build_book_email_html(theme: str, books: list, summary: str, cover_cids: list[str | None] | None = None) -> str:
    safe_theme = escape(theme)
    summary_html = _format_summary(summary)
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
    <div style="font-size:15px; margin-bottom:28px; white-space:normal;">
      {summary_html}
    </div>
    <h2 style="font-size:20px; margin:0 0 16px;">本期书目</h2>
    {book_cards}
  </div>
</body>
</html>"""


def _format_summary(summary: str) -> str:
    paragraphs = []
    for block in summary.split("\n\n"):
        text = block.strip()
        if not text:
            continue
        escaped_text = escape(text).replace("\n", "<br>")
        paragraphs.append(f'<p style="margin:0 0 14px;">{escaped_text}</p>')
    return "".join(paragraphs)


def _build_book_card(book, cover_cid: str | None) -> str:
    title = escape(book.title)
    author = escape(book.author)
    rating = escape(book.rating or "暂无")

    if cover_cid:
        safe_cid = escape(cover_cid)
        cover_html = (
            f'<img src="cid:{safe_cid}" alt="《{title}》封面" '
            'style="display:block; max-width:120px; width:120px; height:auto; border-radius:4px; border:1px solid #ddd;">'
        )
    else:
        cover_html = (
            '<div style="width:120px; min-height:160px; border:1px solid #ddd; border-radius:4px; '
            'display:flex; align-items:center; justify-content:center; color:#777; font-size:14px;">暂无封面</div>'
        )

    return f"""
    <div style="border:1px solid #e5e5e5; border-radius:8px; padding:16px; margin:0 0 16px;">
      <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%; border-collapse:collapse;">
        <tr>
          <td style="width:140px; vertical-align:top; padding-right:16px;">{cover_html}</td>
          <td style="vertical-align:top;">
            <h3 style="font-size:18px; margin:0 0 8px;">《{title}》</h3>
            <p style="margin:0 0 6px; color:#444;">作者：{author}</p>
            <p style="margin:0; color:#444;">评分：{rating}</p>
          </td>
        </tr>
      </table>
    </div>
    """
