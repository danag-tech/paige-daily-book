# Paige - Book Daily

Paige Book Daily 是一个本地和 GitHub Actions 都可运行的每日荐书项目。程序每天从 `config.json` 已配置的主题池中按日期选择主题，联网获取候选图书，过滤历史已发送书籍，调用 DeepSeek 生成中文荐书内容，并通过 QQ 邮箱 SMTP 发送 HTML 邮件。

## 当前流程

```text
Theme Picker 选择当天起始主题
↓
ProviderManager 按主题获取候选书
↓
sent_books.json 过滤已发送书籍
↓
prompt_builder 构建 DeepSeek Prompt
↓
DeepSeek 生成每日荐书正文
↓
下载封面并作为 CID inline image 嵌入 HTML 邮件
↓
QQ SMTP 发送邮件
↓
更新 sent_books.json
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

## 配置

业务配置在 `config.json`：

- `book_count`：每次发送的图书数量，当前为 3。
- `provider_order`：Provider 尝试顺序。
- `theme_strategies`：可用主题及其豆瓣标签/关键词发现策略。
- `pages_per_tag`、`min_rating`、`summary_max_length`、`cover_check_timeout`：图书发现和清洗参数。

`theme_picker.py` 只使用 `config.json` 中已经配置的主题，不会自己生成新主题。

## Provider 行为

`ProviderManager` 会按 `config.json` 中的顺序尝试 Provider。当前主题发现主要由 `RecommendationProvider` 完成：

- 使用豆瓣标签页联网发现候选图书。
- 过滤低于 `min_rating` 的书。
- 综合重复出现次数、评分人数和评分排序。
- 优先用 ISBN 去重。
- 豆瓣封面不可用时，会按后续 Provider 尝试补封面。

如果某个主题搜索时 Provider 抛错，`main.py` 会打印 `Theme failed: ...` 并继续尝试下一个主题。

## 邮件

`email_sender.py` 使用 Python 标准库 `smtplib` 和 `EmailMessage`，默认 QQ 邮箱 SMTP：

```text
smtp.qq.com:465
```

邮件同时包含纯文本正文和 HTML 正文。封面图片由 `cover_image.py` 下载后作为 inline image 附件发送，HTML 中使用 `cid:` 引用。

## GitHub Actions

`.github/workflows/book-daily.yml` 支持手动触发：

```text
workflow_dispatch
```

流程会安装依赖、运行 `python main.py`，成功后提交更新后的 `sent_books.json`。当前没有 cron-job 或 schedule。

## 当前边界

- 不包含定时触发。
- 不包含多邮箱发送。
- 不包含复杂 HTML 模板系统。
- 不包含封面落盘或 base64 图片。
- 不允许重复发送 `sent_books.json` 中已记录的书。
