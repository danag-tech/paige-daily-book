# AGENTS.md

## Project

Paige Book Daily sends a daily Chinese book recommendation email. The current flow is: pick an ordered theme from `config.json`, fetch candidate books through ProviderManager, filter `sent_books.json`, build the fixed prompt, call DeepSeek, build an HTML email with inline cover images, send through QQ SMTP, then update sent history.

## Run

```bash
pip install -r requirements.txt
python main.py
```

Compile check before handoff:

```bash
python -m py_compile main.py theme_picker.py sent_books.py config.py email_sender.py summary_generator.py prompt_builder.py html_email_builder.py cover_image.py
```

## Configuration

Local secrets come from `.env`; GitHub Actions injects the same names through Secrets:

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL` defaults to `deepseek-chat`
- `EMAIL_USER`
- `EMAIL_PASSWORD`
- `EMAIL_TO`

Never print or commit secrets. `.env` must stay ignored.

## Conventions

- Keep changes small and module-scoped.
- Do not redesign ProviderManager or provider architecture for prompt, email, theme, or history tasks.
- Do not modify `prompt_builder.py` unless the task is explicitly about prompt content.
- Do not allow duplicate sent books or delete `sent_books.json` to make tests pass.
- Preserve normal UTF-8 Chinese source text; avoid Unicode escape and mojibake.
- GitHub Actions currently uses manual `workflow_dispatch`; do not add schedule/cron unless explicitly requested.

## Current State

The project has DeepSeek summary generation, QQ SMTP email, HTML email with CID cover images, theme rotation, sent-book deduplication, and manual GitHub Actions support. There is no cron-job, multi-recipient sending, or complex template system.
