# AGENTS.md

## Project

Paige Book Daily sends a daily Chinese book recommendation email and maintains a public GitHub Pages reading site. The current flow is: pick an ordered theme from `config.json`, fetch candidate books through ProviderManager, filter `sent_books.json` and `data/book_pool.json`, build the fixed prompt, call DeepSeek, build an HTML email with inline cover images, send through QQ SMTP, update sent history, generate website JSON, and deploy `website/` through GitHub Pages Actions.

## Run

```bash
pip install -r requirements.txt
python main.py
```

Compile check before handoff:

```bash
python -m py_compile main.py theme_picker.py sent_books.py config.py email_sender.py summary_generator.py prompt_builder.py html_email_builder.py cover_image.py book_pool.py generate_website_data.py
```

Website data can be regenerated without sending email:

```bash
python generate_website_data.py
```

## Configuration

Local secrets come from `.env`; GitHub Actions injects the same names through Secrets:

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL` defaults to `deepseek-chat`
- `EMAIL_USER`
- `EMAIL_PASSWORD`
- `EMAIL_TO`

Never print or commit secrets. `.env` must stay ignored.

## Public Website

The public site lives in `website/` and is deployed by `.github/workflows/book-daily.yml` using GitHub Pages Actions.

- `website/index.html`: home page with today's three books, a front-end-only subscription display, and the recent 15-book archive.
- `website/book.html`: detail page, loaded as `book.html?id=xxx`.
- `website/books.json`: recent 15 recommended books.
- `website/today.json`: today's three recommended books.
- `generate_website_data.py`: converts `sent_books.json` into public website data.

Only public display fields should be exposed in website JSON: `title`, `author`, `rating`, `cover`, `summary`, `recommended_date`, `detail_url`, `weread_url`. Do not expose internal keys, ISBN, provider source, theme strategy details, local paths, emails, or secrets.

## Conventions

- Keep changes small and module-scoped.
- Do not redesign ProviderManager or provider architecture for prompt, email, theme, website, or history tasks.
- Do not modify `prompt_builder.py` unless the task is explicitly about prompt content.
- Do not allow duplicate sent books or delete `sent_books.json` to make tests pass.
- Preserve normal UTF-8 Chinese source text; avoid Unicode escape and mojibake.
- GitHub Actions currently uses manual `workflow_dispatch`; do not add schedule/cron unless explicitly requested.
- `archive/` is local-only and ignored. Do not commit archived personal test history unless explicitly requested.

## Current State

The project has DeepSeek summary generation, QQ SMTP email, HTML email with CID cover images, theme rotation, book pool fallback, sent-book deduplication, manual GitHub Actions support, and a GitHub Pages public website. There is no cron-job, multi-recipient sending, real public subscription backend, or complex template system.
