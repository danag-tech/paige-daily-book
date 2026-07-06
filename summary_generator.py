import requests

from config import DeepSeekConfig


DEEPSEEK_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"


class SummaryGenerationError(RuntimeError):
    pass


def generate_summary(prompt: str, config: DeepSeekConfig) -> str:
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
