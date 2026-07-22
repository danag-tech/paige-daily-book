# Paige Book Daily

Paige Book Daily 是一个自动生成中文每日荐书内容的项目。它按配置选择主题，从多个图书来源获取候选书，过滤已推荐记录，调用 DeepSeek 生成荐书内容，通过 QQ SMTP 发送 HTML 邮件，并同步维护一个 GitHub Pages 阅读网站。

当前公开网站：<https://danag-tech.github.io/paige-daily-book/>

当前版本状态：`v1.2` 基础流程已完成；`v1.3` 邮箱订阅 MVP 已接入每日邮件收件人选择。网站表单向 Supabase `subscribers` 表提交邮箱；每日任务读取 `active = true` 的订阅用户并发送邮件。若 Supabase 未配置、读取失败或没有 active 用户，则继续使用 `EMAIL_TO` fallback。Supabase 表结构、唯一约束、RLS 策略和 GitHub Secrets 属于外部配置，不由本仓库修改。

## 当前功能

- 按 `config.json` 中的有序主题策略选择当天主题。
- 通过 ProviderManager 获取候选图书，并按 Provider 顺序降级。
- 使用 `sent_books.json` 防止重复推荐，使用 `data/book_pool.json` 缓存候选书。
- 使用固定 prompt 调用 DeepSeek 生成每日荐书正文和单书简介。
- 下载封面并以内嵌 CID 图片生成 HTML 邮件，通过 QQ SMTP 发送。
- 发送成功后更新荐书历史、候选池和网站 JSON 数据。
- GitHub Pages 网站展示今日 3 本书和最近 15 本荐书，并提供单书详情页。
- 首页邮箱表单将邮箱规范化为小写后，通过 Supabase REST API 写入 `subscribers`。
- 每日邮件优先发送给 Supabase 中 active 的唯一邮箱；订阅读取不可用时回退到 `EMAIL_TO`。

## 技术架构

```text
config.json
  -> theme_picker.py
  -> providers/manager.py
  -> sent_books.json + data/book_pool.json
  -> prompt_builder.py
  -> summary_generator.py / DeepSeek
  -> cover_image.py + html_email_builder.py
  -> subscribers.py / active subscribers
  -> email_sender.py / QQ SMTP
  -> sent_books.json + data/book_pool.json
  -> generate_website_data.py
  -> website/today.json + website/books.json + website/covers/
  -> GitHub Pages
```

邮箱订阅写入链路：

```text
website/index.html
  -> website/site_config.js
  -> Supabase REST API
  -> subscribers
```

邮件收件人选择由 `email_sender.py` 完成：先读取 `subscribers.py` 返回的 active 邮箱；返回空列表或读取异常时使用 `EMAIL_TO`。这不会改变选书、DeepSeek、prompt、简介或 HTML 邮件模板。

## 项目结构

- `main.py`：每日荐书流程入口。
- `config.py`：环境变量和运行配置读取。
- `config.json`：选书数量、Provider 顺序、主题策略和筛选参数。
- `providers/`：图书来源及 ProviderManager。
- `theme_picker.py`：主题轮换。
- `sent_books.py`：荐书历史读取、去重和保存。
- `book_pool.py`：候选书池读取、刷新和保存。
- `prompt_builder.py`：固定 DeepSeek prompt 构建。
- `summary_generator.py`：DeepSeek 调用和结果解析。
- `subscribers.py`：读取 Supabase active subscriber 邮箱。
- `cover_image.py`：封面下载和邮件内嵌图片准备。
- `html_email_builder.py`：HTML 邮件内容生成。
- `email_sender.py`：收件人解析和 QQ SMTP 邮件发送。
- `generate_website_data.py`：从历史记录生成公开网站 JSON 和封面资源。
- `website/`：GitHub Pages 静态网站。
- `.github/workflows/book-daily.yml`：手动触发的荐书、数据提交和 GitHub Pages 部署流程。
- `archive/`：本地归档目录，已被忽略，不提交个人测试历史。

公开网站 JSON 只允许包含：`title`、`author`、`rating`、`cover`、`summary`、`recommended_date`、`detail_url`、`weread_url`。不得暴露 ISBN、Provider 来源、主题策略、内部 key、邮箱、路径或密钥。

## 配置

本地运行使用根目录 `.env`；GitHub Actions 需要将同名 Secrets 注入每日任务。`.env` 已被 `.gitignore` 忽略，禁止打印或提交密钥。

```text
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_MODEL=deepseek-chat
EMAIL_USER=你的 QQ 发件邮箱
EMAIL_PASSWORD=你的 QQ 邮箱授权码
EMAIL_TO=无订阅用户时的 fallback 收件邮箱
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=每日任务读取 subscribers 使用的服务端密钥
```

`EMAIL_TO` 可以为空；有 active subscribers 时优先使用订阅邮箱。若订阅未配置、读取失败或没有 active 用户，必须保留 `EMAIL_TO` 作为 fallback。`SUPABASE_KEY` 只能作为服务端 Secret 使用，不能写入网站；网站继续使用单独生成的公开 `SUPABASE_ANON_KEY` 配置。

Supabase 需要人工配置：

- `subscribers.email` 唯一约束。
- 浏览器插入所需的最小 RLS 策略。
- GitHub Secrets：`SUPABASE_URL`、`SUPABASE_KEY`，以及网站部署使用的 `SUPABASE_ANON_KEY`。

本项目不修改数据库结构、RLS 或数据迁移。

## 本地运行

安装依赖：

```bash
pip install -r requirements.txt
```

执行一次完整荐书流程（会调用外部服务并发送邮件）：

```bash
python main.py
```

只重新生成网站数据、不发送邮件：

```bash
python generate_website_data.py
```

交接前编译检查：

```bash
python -m py_compile main.py theme_picker.py sent_books.py config.py email_sender.py summary_generator.py prompt_builder.py html_email_builder.py cover_image.py book_pool.py generate_website_data.py subscribers.py
```

## 部署方式

`.github/workflows/book-daily.yml` 当前仅支持 `workflow_dispatch` 手动触发，不包含 schedule/cron。每日任务需要把 `SUPABASE_URL` 和 `SUPABASE_KEY` 注入 `python main.py` 所在步骤；网站部署仍使用 `SUPABASE_ANON_KEY` 生成临时的 `website/site_config.js`。工作流的触发方式和现有部署步骤不变。

GitHub Actions 的提交和部署状态应以 GitHub 工作流记录为准；本地仓库不能证明远端 Secrets、Supabase RLS 或线上订阅写入已经配置成功。

## 当前边界

- 没有定时触发；每日任务需要手动运行工作流。
- Supabase active subscriber 读取失败时会 fallback 到 `EMAIL_TO`，避免破坏个人使用方式。
- 当前没有退订页面、确认邮件、反滥用限制或数据保留策略。
- Supabase schema、唯一约束、RLS 和 Secrets 不由当前仓库管理。
- 不包含复杂模板系统，也不允许通过删除历史文件绕过荐书去重。

## 后续规划

1. 完成 GitHub Secrets 注入并进行一次不发送真实邮件的端到端配置检查。
2. 在 Supabase 中确认唯一约束、RLS 和 active 状态维护方式。
3. 增加退订、确认邮件、隐私说明和反滥用策略。
4. 评估批量收件的隐私保护方式，例如 Bcc 或独立投递。

后续改动必须保持 Provider、选书逻辑、DeepSeek 调用、prompt、简介生成、HTML 邮件模板和现有部署触发方式稳定，除非任务明确授权修改这些区域。
