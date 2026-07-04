# Paige - Book Daily

Module 1.1: Book Source MVP with online theme discovery.

输入一个主题，程序会根据 `config.json` 中的主题发现策略联网寻找候选图书，并输出该主题下 3 本代表性中文书：

- 书名
- 作者
- ISBN
- 评分
- 封面 URL
- 简介
- 主题来源
- 书籍信息来源

## 当前规则

- 不维护固定书名列表。
- 主题配置只保存发现策略：`tags` 和 `keywords`。
- 当前 `RecommendationProvider` 使用豆瓣标签页联网发现候选书。
- 先过滤豆瓣评分低于 `7.5` 的书。
- 候选书排序综合：
  - 多个标签/关键词结果中重复出现次数
  - 评分人数
  - 评分
- 返回前 3 本，并优先使用 ISBN 去重。
- 评分统一输出为 `⭐7.9` 格式。
- 原始简介最多保留 `800` 字，后续 Module 2 再由 AI 压缩成 300-500 字。
- 会检查封面 URL 是否可访问；如果失效，会按后续 Provider 顺序尝试获取替代封面。
- 如果 Provider 无法支持主题推荐，必须明确报不支持，不能降级成关键词搜索。

## 运行

```bash
pip install -r requirements.txt
python main.py
```

当前主题在 `main.py` 中写死为：

```python
theme = "认知升级"
```

## 配置

所有可配置项都在 `config.json`：

```json
{
  "provider_order": [
    "recommendation",
    "weread",
    "openlibrary",
    "googlebooks"
  ],
  "book_count": 3,
  "min_rating": 7.5,
  "summary_max_length": 800,
  "cover_check_timeout": 3,
  "pages_per_tag": 2,
  "theme_source": "config.json 主题发现策略 + 豆瓣标签页联网发现",
  "theme_strategies": {
    "认知升级": {
      "tags": [
        "思维",
        "认知科学",
        "心理学",
        "决策"
      ],
      "keywords": [
        "认知升级 书单",
        "思维升级 书单"
      ]
    }
  }
}
```

`tags` 会直接访问豆瓣读书标签页。`keywords` 会清洗成额外标签候选，例如 `认知升级 书单` 会尝试访问 `认知升级` 标签页。

## Provider 行为

ProviderManager 会按顺序尝试：

1. RecommendationProvider
2. WeRead
3. OpenLibrary
4. GoogleBooks

当前只有 `RecommendationProvider` 支持主题发现。微信读书、OpenLibrary、GoogleBooks 不支持主题推荐时会明确报错，不会退化成主题关键词搜索。

OpenLibrary 和 GoogleBooks 当前可作为封面兜底来源：当上游封面 URL 不可访问时，程序会尝试用 ISBN 获取替代封面。

## 当前边界

本阶段只包含 Module 1 / Module 1.1（Book Source MVP）：

- 不包含 AI
- 不包含邮件
- 不包含 GitHub Actions
- 不包含 cron-job
