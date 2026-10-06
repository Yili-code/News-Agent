"""Select one source-grounded story and hand it to the private social editor."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from news_agent import AgentBrain, GEMINI_API_KEY, NewsFetcher  # noqa: E402


def configure_utf8_output() -> None:
    """Keep Chinese dry-run output readable on legacy Windows consoles."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8", errors="backslashreplace")


def parse_json_response(raw: str) -> dict:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw or "")
    cleaned = re.sub(r"^\s*```(?:json)?|```\s*$", "", cleaned).strip()
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Model response is not an object")
    return value


def select_candidate(news_items: list[dict], brain: AgentBrain | None = None) -> dict | None:
    if not news_items:
        return None
    brain = brain or AgentBrain()
    candidates = [
        item for item in brain.dedupe_news_items(news_items)
        if str(item.get("link", "")).startswith("https://")
        and str(item.get("title", "")).strip()
        and str(item.get("summary", "")).strip()
    ]
    if not candidates:
        return None

    compact = [
        {
            "number": index,
            "category": item.get("category", ""),
            "source": item.get("source", ""),
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "summary": item.get("summary", ""),
        }
        for index, item in enumerate(candidates[:18], 1)
    ]
    prompt = """你在替 YiLi 的私人社群編輯選擇今天唯一值得詢問的新聞候選，不是在直接寫貼文。

優先選擇能引出具體技術、產品或創業判斷的事件；不要只因為公司知名、融資金額大或話題熱門而選。只能使用輸入摘要支持的事實，不可假裝讀過全文或杜撰使用者反應。若沒有合格候選，selected_number 回傳 0。

fact_summary 用繁體中文寫一至兩句來源可支持的事實。question_one 問 YiLi 第一個具體反應；question_two 問這件事改變了他對什麼產品、技術或創業判斷。問題要針對該新聞，不可每天都像固定問卷。

只輸出 JSON：{"selected_number":1,"fact_summary":"...","question_one":"...","question_two":"..."}。"""
    response = brain.client.models.generate_content(
        model=brain.model_name,
        contents=f"{prompt}\n\n候選新聞：\n{json.dumps(compact, ensure_ascii=False)}",
    )
    selected = parse_json_response(response.text or "")
    number = selected.get("selected_number")
    if number == 0:
        return None
    if not isinstance(number, int) or number < 1 or number > len(compact):
        raise ValueError("Model selected an invalid candidate")
    for field in ("fact_summary", "question_one", "question_two"):
        if not isinstance(selected.get(field), str) or not selected[field].strip():
            raise ValueError(f"Model omitted {field}")

    item = candidates[number - 1]
    identity_seed = (item.get("link") or item.get("title") or "").encode("utf-8")
    return {
        "id": hashlib.sha256(identity_seed).hexdigest()[:24],
        "source_name": str(item.get("source", "Unknown source"))[:200],
        "category": str(item.get("category", "Uncategorized"))[:120],
        "title": str(item.get("title", "Untitled"))[:500],
        "url": str(item.get("link", "")),
        "source_summary": str(item.get("summary", ""))[:3500],
        "fact_summary": selected["fact_summary"].strip()[:800],
        "question_one": selected["question_one"].strip()[:500],
        "question_two": selected["question_two"].strip()[:500],
    }


def submit_candidate(candidate: dict, endpoint: str, token: str) -> dict:
    response = requests.post(
        endpoint.rstrip("/") + "/internal/candidates",
        headers={"Authorization": f"Bearer {token}"},
        json=candidate,
        timeout=30,
    )
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Social editor returned HTTP {response.status_code}") from exc
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Social editor rejected candidate: HTTP {response.status_code} {result.get('error', '')}")
    return result


def run(dry_run: bool = False) -> bool:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required")
    endpoint = os.getenv("SOCIAL_EDITOR_URL", "")
    token = os.getenv("SOCIAL_EDITOR_JOB_TOKEN", "")
    if not dry_run and (not endpoint.startswith("https://") or not token):
        raise RuntimeError("SOCIAL_EDITOR_URL (https) and SOCIAL_EDITOR_JOB_TOKEN are required")

    items = NewsFetcher(limit_per_source=3).fetch_news()
    candidate = select_candidate(items)
    if not candidate:
        print("No source-grounded candidate today; nothing was sent.")
        return False
    if dry_run:
        print(json.dumps(candidate, ensure_ascii=False, indent=2))
        return True
    result = submit_candidate(candidate, endpoint, token)
    print(f"Social editor candidate: {result.get('status', 'accepted')}")
    return result.get("status") in {"sent", "duplicate", "busy"}


if __name__ == "__main__":
    configure_utf8_output()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Select and print a candidate without contacting Telegram or social platforms")
    args = parser.parse_args()
    raise SystemExit(0 if run(args.dry_run) else 1)
