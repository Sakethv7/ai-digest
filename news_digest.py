import os, datetime as dt
from dateutil import tz
import requests
from openai import OpenAI

MODEL = "gpt-4.1-mini"
TIMEZONE = "America/New_York"
QUERIES = [
  "latest AI research breakthroughs and open-source LLM releases",
  "AI policy & regulation updates in US, EU, and India this week",
  "AI chip industry news (NVIDIA, AMD, TSMC, Intel)",
  "big-tech AI product launches (OpenAI, Google, Microsoft, Anthropic, Meta)",
  "safety & governance news (AI risk, standards, elections, misuse)"
]
DOMAIN_WHITELIST = [
  "arxiv.org","semianalysis.com","theverge.com","techcrunch.com","wired.com",
  "noahpinion.blog","whitehouse.gov","europa.eu","ft.com","reuters.com",
  "washingtonpost.com","nytimes.com","apnews.com","mit.edu","stanford.edu"
]

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
client = OpenAI(api_key=OPENAI_API_KEY)

today = dt.datetime.now(tz.gettz(TIMEZONE)).date().isoformat()

prompt = f"""You are a news desk editor. Produce a concise daily digest for Slack:
- Topic: AI/tech + surrounding politics/policy
- Date: {today} ({TIMEZONE})
- Use web search to find FRESH items from the last 48–72 hours where possible.
- Prioritize reputable outlets; prefer these domains when relevant: {", ".join(DOMAIN_WHITELIST)}.
- Group into 3–5 sections (e.g., Research, Policy, Chips, Product Launches, Wildcards).
- 1–2 bullets per item: bold headline, 1-sentence takeaway, and include a citation link.
- Keep total ~10–14 items.
Return Markdown suitable for Slack (bold, links)."""

resp = client.responses.create(
    model=MODEL,
    input=[{"role":"user","content": prompt}],
    tools=[{"type":"web_search"}],
    tool_choice="auto",
    temperature=0.3,
    max_output_tokens=1400,
)

def get_text(r):
    parts = []
    for item in r.output:
        if item.type == "message":
            for c in item.message.content:
                if c.type == "output_text":
                    parts.append(c.text)
    return "\n".join(parts).strip()

digest_md = get_text(resp)

blocks = [
  {"type":"header","text":{"type":"plain_text","text":f"📰 AI/Tech + Policy Digest — {today}"}},
  {"type":"section","text":{"type":"mrkdwn","text":digest_md}}
]
res = requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks}, timeout=30)
res.raise_for_status()
print("Posted to Slack.")
