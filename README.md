# Paige - Book Daily

Paige Book Daily 是一个本地和 GitHub Actions 都可运行的每日中文荐书项目。它会按主题获取候选图书，过滤已推荐历史，调用 DeepSeek 生成中文荐书内容，通过 QQ 邮箱 SMTP 发送 HTML 邮件，并同步生成一个 GitHub Pages 公开展示网站。

当前版本：`v1.2.1`。公开网站入口为 GitHub Pages：`https://danag-tech.github.io/paige-daily-book/`。

## 当前流程

```text
Theme Picker 选择当天起始主题
↓
ProviderManager 按主题获取候选书
↓
sent_books.json + data/book_pool.json 过滤和补充候选
↓
prompt_builder 构建固定 DeepSeek Prompt
↓
DeepSeek 生成每日荐书正文
↓
下载封面并作为 CID inline image 嵌入 HTML 邮件
↓
QQ SMTP 发送邮件
↓
更新 sent_books.json 和 data/book_pool.json
↓
generate_website_data.py 更新 website/today.json 和 website/books.json
↓
GitHub Actions 提交数据并部署 website/ 到 GitHub Pages
```

如果当天主题搜索失败或未发送书不足，`main.py` 会继续尝试 `theme_picker.get_ordered_themes()` 中的下一个已配置主题。所有主题都失败或都不足时，程序以非零状态退出，方便 GitHub Actions 显示失败。

## 运行

```bash
pip install -r requirements.txt
python main.py
```

本地运行需要 `.env`，GitHub Actions 通过 Secrets 注入同名环境变量。

必需配置：

```text
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_MODEL=deepseek-chat
EMAIL_USER=你的 QQ 发件邮箱
EMAIL_PASSWORD=你的 QQ 邮箱授权码
EMAIL_TO=收件邮箱
```

`DEEPSEEK_MODEL` 默认值是 `deepseek-chat`。

交接前可运行语法检查：

```bash
python -m py_compile main.py theme_picker.py sent_books.py config.py email_sender.py summary_generator.py prompt_builder.py html_email_builder.py cover_image.py book_pool.py generate_website_data.py
```

## 配置

业务配置在 `config.json`：

- `book_count`：每次发送的图书数量，当前为 3。
- `provider_order`：Provider 尝试顺序。
- `theme_strategies`：可用主题及其豆瓣标签/关键词发现策略。
- `pages_per_tag`、`min_rating`、`summary_max_length`、`cover_check_timeout`：图书发现和清洗参数。

`theme_picker.py` 只使用 `config.json` 中已经配置的主题，不会自己生成新主题。

## Provider 行为

`ProviderManager` 会按 `config.json` 中的顺序尝试 Provider。豆瓣推荐源仍是优先数据源；当豆瓣不可用、返回不足或出现异常时，系统会尝试后续备用 Provider。

当前 Provider 目录包含：

- `recommendation.py`：主题推荐主 Provider，优先使用豆瓣标签页。
- `googlebooks.py`：Google Books 备用源，包含中文质量过滤。
- `openlibrary.py`：Open Library 备用源，包含中文质量过滤。
- `weread.py`：微信读书备用源占位/扩展入口。
- `manager.py`：Provider 调度和失败降级。

## 历史与候选池

- `sent_books.json`：已发送历史，用于防止重复推荐。
- `data/book_pool.json`：候选书缓存池，用于提高豆瓣不可用时的稳定性。
- `archive/`：本地归档目录，已在 `.gitignore` 中，不提交到仓库。

去重同时考虑 ISBN key 和 `title + author` key。不要为了测试通过而删除 `sent_books.json` 或允许重复书。

## 邮件

`email_sender.py` 使用 Python 标准库 `smtplib` 和 `EmailMessage`，默认 QQ 邮箱 SMTP：

```text
smtp.qq.com:465
```

邮件同时包含纯文本正文和 HTML 正文。封面图片由 `cover_image.py` 下载后作为 inline image 附件发送，HTML 中使用 `cid:` 引用。

## 公开网站

公开网站文件位于 `website/`：

- `index.html`：首页，包含今日推荐、邮箱订阅展示模块、最近 15 本荐书。
- `book.html`：单本书详情页，使用 `book.html?id=xxx` 从 `books.json` 读取完整图书信息。
- `style.css`：手机优先的阅读网站样式。
- `today.json`：今日推荐 3 本书。
- `books.json`：最近 15 本荐书历史。

`generate_website_data.py` 从 `sent_books.json` 生成公开数据，只输出前端需要的字段：

```text
title, author, rating, cover, summary, recommended_date, detail_url, weread_url
```

生成逻辑会过滤内部 key、ISBN、source、theme 等字段，并清理明显营销式简介、Markdown 标记和装饰性推荐语。

## GitHub Actions

`.github/workflows/book-daily.yml` 当前为手动触发：

```text
workflow_dispatch
```

工作流会：

1. 安装依赖。
2. 运行 `python main.py`。
3. 提交更新后的 `sent_books.json`、`data/book_pool.json`、`website/books.json`、`website/today.json`。
4. 使用 GitHub Pages Actions 部署 `website/`。

当前 workflow 保留：

```yaml
concurrency:
  group: book-daily
  cancel-in-progress: false
```

当前没有 cron-job 或 schedule。

## 当前边界

- 不包含定时触发。
- 不包含多邮箱发送。
- 不包含真实公开订阅功能；首页订阅模块仅为前端展示。
- 不包含复杂 HTML 模板系统。
- 不包含封面落盘或 base64 图片。
- 不允许重复发送 `sent_books.json` 中已记录的书。
