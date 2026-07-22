# AGENTS.md

## 项目定位

Paige Book Daily 是中文每日荐书项目：按 `config.json` 选主题，获取并去重图书，调用 DeepSeek 生成荐书内容，通过 QQ SMTP 发信，并生成 GitHub Pages 网站数据。当前 `v1.2` 基础流程已完成，`v1.3` 正在开发邮箱订阅；订阅前端已写入 Supabase REST 链路，但数据库 schema、RLS 和远端 Secrets 属于外部待确认项。

## 项目结构

- `main.py`：每日任务入口。
- `config.py`、`.env.example`：运行配置和环境变量示例。
- `config.json`、`theme_picker.py`：主题和选书参数。
- `providers/`：Provider 实现与 `ProviderManager`。
- `sent_books.py`、`sent_books.json`：历史去重。
- `book_pool.py`、`data/book_pool.json`：候选池。
- `prompt_builder.py`、`summary_generator.py`：固定 prompt 和 DeepSeek 生成。
- `cover_image.py`、`html_email_builder.py`、`email_sender.py`：封面、邮件内容和 QQ SMTP。
- `generate_website_data.py`、`website/`：公开网站数据、静态页面和封面资源。
- `.github/workflows/book-daily.yml`：手动触发的荐书和 GitHub Pages 部署。
- `archive/`：本地忽略目录，不提交个人测试历史。

## 运行与验证

```bash
pip install -r requirements.txt
python main.py
python generate_website_data.py
```

交接前必须运行编译检查：

```bash
python -m py_compile main.py theme_picker.py sent_books.py config.py email_sender.py summary_generator.py prompt_builder.py html_email_builder.py cover_image.py book_pool.py generate_website_data.py
```

完整运行会调用外部 Provider、DeepSeek 和 SMTP；没有对应密钥时只做编译检查或针对性静态检查，不伪造成功结果。修改网站订阅时，还应单独验证表单输入、Supabase 配置缺失、成功、重复邮箱和失败响应。

## 修改规范

- 保持改动小而模块化；先查现有实现和数据流，再修改最小必要文件。
- 正常使用 UTF-8 中文文本；不要引入 Unicode 转义、乱码或无关格式重写。
- 不删除 `sent_books.json`，不放宽去重逻辑来让测试通过。
- 公开网站 JSON 只能输出公开字段：`title`、`author`、`rating`、`cover`、`summary`、`recommended_date`、`detail_url`、`weread_url`。
- 不打印、复制或提交 `.env`、API key、密码、token、邮箱隐私数据或本地敏感路径。
- `website/site_config.js` 由工作流生成并被忽略；网站只能使用 Supabase anon key，不能使用 service role key。
- `archive/` 仅供本地使用，除非任务明确要求，不提交其中内容。

## 默认不可修改区域

除非任务明确授权，禁止修改：

- Provider 实现、ProviderManager 和 Provider 架构。
- DeepSeek 调用逻辑、固定 prompt 和 summary 生成逻辑。
- 邮件内容生成逻辑和现有 QQ SMTP 发送流程。
- `.github/workflows/book-daily.yml` 的现有触发、荐书、提交和部署流程。
- `website/` 中与当前功能无关的网站页面、样式和前端行为。

订阅任务只应修改订阅所需的前端、Supabase 配置说明或文档；不得顺手重构荐书或邮件主链路。

## Git 规范

- 修改前后检查 `git status`，保留用户已有改动，不使用 `git reset --hard` 或覆盖性 checkout。
- 提交信息使用简短、明确的类型前缀，例如 `docs: update project handoff docs`、`fix: handle duplicate subscription`。
- 一次提交只包含一个逻辑主题；不要把生成的个人归档、密钥、临时文件或无关格式化混入提交。
- 本项目默认不自动 commit、push 或创建 PR；只有用户明确要求时才执行。
- 不新增 schedule/cron，不改变 GitHub Actions 的手动触发约束，除非任务明确授权。
