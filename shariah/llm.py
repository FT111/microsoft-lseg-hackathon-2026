"""Azure OpenAI via the organisers' portal. Key comes from .env (OPENAI_API_KEY),
never from code. Every call is cached so the demo can replay offline."""
import hashlib
import json
import os
import re

from dotenv import load_dotenv

from .cache import cached

load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://app-uoaihack2ix6ak.azurewebsites.net")
MODEL = os.getenv("CHAT_MODEL", "gpt-6-astra")
API_VERSION = "2024-12-01-preview"


def available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _client():
    from openai import AzureOpenAI
    return AzureOpenAI(api_version=API_VERSION, azure_endpoint=ENDPOINT, api_key=os.getenv("OPENAI_API_KEY"))


def ask(system: str, user: str, max_tokens: int = 1500) -> str:
    key = "llm_" + hashlib.sha1((MODEL + system + user).encode()).hexdigest()[:16]
    def produce():
        r = _client().chat.completions.create(
            model=MODEL, max_completion_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return r.choices[0].message.content
    return cached(key, produce)


BUSINESS_SYSTEM = """You screen companies for Shariah compliance (business-activity screen only).
Non-compliant activities: conventional (interest-based) banking, finance and insurance; alcohol;
pork and non-halal food processing; gambling, casinos, cinema, music, adult entertainment, hotels;
tobacco; weapons and defence.
Read the 10-K business section you are given. Estimate the share of total revenue that comes
DIRECTLY from non-compliant activities as a main line of business. Ancillary features, optional
add-ons, and products that merely carry third-party content do not count unless the text shows
they are a material revenue line. Do NOT include interest income (it is measured separately).
Only use the text given; if it does not quantify the revenue, give your best estimate and set
confidence to "low".
Reply with JSON only:
{"noncompliant_pct": number 0-100, "categories": [strings], "evidence": "one short verbatim quote from the text",
 "confidence": "high"|"medium"|"low", "reasoning": "one sentence"}"""


def business_screen(name: str, item1_text: str) -> dict:
    raw = ask(BUSINESS_SYSTEM, f"Company: {name}\n\n10-K Item 1 (excerpt):\n{item1_text}", 600)
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        out = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        out = {}
    if "noncompliant_pct" not in out:
        return {"noncompliant_pct": None, "categories": ["model reply unreadable"], "evidence": raw[:200],
                "confidence": "low", "method": "LLM"}
    out["method"] = "LLM"
    return out
