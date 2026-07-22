import json
import re
from dataclasses import dataclass

import requests

from config import DeepSeekConfig


DEEPSEEK_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"
MIN_CHINESE_SUMMARY_CHARACTERS = 150
MAX_CHINESE_SUMMARY_CHARACTERS = 250
SUMMARY_VALIDATION_ATTEMPTS = 3


class SummaryGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedSummary:
    daily_text: str
    book_summaries: list[str]


def generate_summary(prompt: str, config: DeepSeekConfig) -> str:
    return generate_summary_result(prompt, config).daily_text


def generate_summary_result(prompt: str, config: DeepSeekConfig) -> GeneratedSummary:
    last_validation_error = None
    for _ in range(SUMMARY_VALIDATION_ATTEMPTS):
        content = _request_summary_content(prompt, config)
        result = _parse_generated_summary(content)
        try:
            _validate_summary_lengths(result.book_summaries)
        except SummaryGenerationError as exc:
            last_validation_error = exc
            continue
        return result

    raise SummaryGenerationError(
        f"DeepSeek summary failed the {MIN_CHINESE_SUMMARY_CHARACTERS}-{MAX_CHINESE_SUMMARY_CHARACTERS} "
        "Chinese-character length check after "
        f"{SUMMARY_VALIDATION_ATTEMPTS} attempts."
    ) from last_validation_error


def _validate_summary_lengths(summaries: list[str]) -> None:
    invalid_summaries = []
    for index, summary in enumerate(summaries, start=1):
        chinese_character_count = _count_chinese_characters(summary)
        if not MIN_CHINESE_SUMMARY_CHARACTERS <= chinese_character_count <= MAX_CHINESE_SUMMARY_CHARACTERS:
            invalid_summaries.append(f"books[{index}]={chinese_character_count}")

    if invalid_summaries:
        details = ", ".join(invalid_summaries)
        raise SummaryGenerationError(
            "Summary length must be "
            f"{MIN_CHINESE_SUMMARY_CHARACTERS}-{MAX_CHINESE_SUMMARY_CHARACTERS} "
            f"Chinese characters: {details}."
        )


def _count_chinese_characters(text: str) -> int:
    return len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))


def _request_summary_content(prompt: str, config: DeepSeekConfig) -> str:
    if not config.api_key:
        raise SummaryGenerationError("DEEPSEEK_API_KEY is missing. Please set it in .env before running the program.")

    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            DEEPSEEK_CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
    except requests.Timeout as exc:
        raise SummaryGenerationError("DeepSeek API request timed out after 60 seconds.") from exc
    except requests.RequestException as exc:
        raise SummaryGenerationError(f"DeepSeek API request failed: {exc}") from exc

    if response.status_code != 200:
        response_text = response.text[:500] if response.text else "empty response body"
        raise SummaryGenerationError(
            f"DeepSeek API returned HTTP {response.status_code}: {response_text}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise SummaryGenerationError("DeepSeek API returned invalid JSON.") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SummaryGenerationError("DeepSeek API response structure is missing choices[0].message.content.") from exc

    if not isinstance(content, str) or not content.strip():
        raise SummaryGenerationError("DeepSeek API returned empty summary content.")

    return content.strip()


def _parse_generated_summary(content: str) -> GeneratedSummary:
    json_text = _extract_json_object(content)
    try:
        data = json.loads(json_text)
    except ValueError as exc:
        raise SummaryGenerationError("DeepSeek summary content is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise SummaryGenerationError("DeepSeek summary JSON must be an object.")

    daily_text = data.get("daily_text")
    if not isinstance(daily_text, str) or not daily_text.strip():
        raise SummaryGenerationError("DeepSeek summary JSON is missing non-empty daily_text.")

    books = data.get("books")
    if not isinstance(books, list) or len(books) != 3:
        raise SummaryGenerationError("DeepSeek summary JSON must include exactly 3 books.")

    book_summaries: list[str] = []
    for index, item in enumerate(books, start=1):
        if not isinstance(item, dict):
            raise SummaryGenerationError(f"DeepSeek summary JSON books[{index}] must be an object.")
        summary = item.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise SummaryGenerationError(f"DeepSeek summary JSON books[{index}].summary is empty.")
        book_summaries.append(summary.strip())

    return GeneratedSummary(
        daily_text=daily_text.strip(),
        book_summaries=book_summaries,
    )


def _extract_json_object(content: str) -> str:
    text = content.strip()
    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        text = fenced_match.group(1).strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise SummaryGenerationError("DeepSeek summary content does not contain a JSON object.")

    return text[start : end + 1]
