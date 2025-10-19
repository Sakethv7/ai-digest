import os
import re
import datetime as dt
from dateutil import tz
import requests
import google.generativeai as genai

# Configuration
TIMEZONE = "America/New_York"
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U07DZBQGXDK")  # Optional mention id

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

today = dt.datetime.now(tz.gettz(TIMEZONE)).date().isoformat()
current_time = dt.datetime.now(tz.gettz(TIMEZONE)).strftime('%I:%M %p %Z')

print("🚀 Starting AI News Digest with Gemini...")
print(f"📅 Date: {today}")

# List available models (debug)
print("📋 Checking available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"  ✓ {m.name}")
except Exception as e:
    print(f"  ⚠️  Could not list models: {e}")

# Pick model
model = None
for name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]:
    try:
        model = genai.GenerativeModel(name)
        print(f"✅ Using model: {name}")
        break
    except Exception as e:
        print(f"⚠️  {name} not available: {e}")
if model is None:
    raise SystemExit("No Gemini model available")

prompt = f"""You are an expert AI/tech news editor creating today's digest for {today} ({TIMEZONE}).

**Task:** Create a clean, focused daily digest covering USA, India, and key global AI developments.

**Required Sections (IN THIS ORDER):**

1. 🇺🇸 USA Tech & AI
   - Focus: Major AI companies (OpenAI, Google, Microsoft, Anthropic, Meta)
   - US government AI policies, regulations, funding initiatives
   - Product launches, new AI models, research breakthroughs

2. 🇮🇳 India Tech & AI
   - Focus: Indian AI startups, government initiatives
   - Major funding rounds, product launches
   - IIT/academic research, local AI developments

3. 🌏 Global AI News
   - Focus: China AI developments, Japan tech initiatives
   - EU AI policies and regulations (focus on policy, not random tech news)
   - Major international AI partnerships and projects

4. 💰 Funding & M&A
   - Major AI/tech funding rounds (>$20M)
   - Acquisitions, IPOs, strategic investments
   - Focus on AI-related deals globally

5. 🚀 Product Launches
   - New AI products, features, tools
   - Major software/hardware releases
   - Focus on practical, newsworthy launches

6. 🎯 Notable Mentions
   - Interesting breakthroughs, controversies
   - Policy changes, industry shifts
   - Wild cards worth knowing

**Format Requirements:**
- Section headers: emoji + **bold text** (use **Header Name**)
- Each bullet: Plain text headline - Plain text description
- NO bold in bullet points, only in section headers
- NO markdown except bullets (•) and section headers
- 2-3 items per section
- Keep descriptions to 1-2 sentences

Create the digest now:"""

try:
    print("🤖 Generating digest with Gemini...")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=3000,
        ),
    )
    digest_text = (response.text or "").strip()

    # --- Normalize formatting for Slack (bold uses single asterisks) ---

    # Remove stray markdown noise
    digest_text = digest_text.replace('---', '').replace('##', '').replace('###', '')

    lines = digest_text.splitlines()
    cleaned = []
    section_emoji = ['🇺🇸', '🇮🇳', '🌏', '💰', '🚀', '🎯']

    for line in lines:
        s = line.strip()

        # Convert **Header** → *Header* ONLY for section headers (lines with emoji)
        if any(e in s for e in section_emoji):
            # Replace exactly one bold wrapper (avoid touching bullets)
            s = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', s)

        # For bullet lines, strip any accidental bold/italics
        if s.startswith('•'):
            s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)   # remove double-bold
            s = re.sub(r'\*([^*]+)\*', r'\1', s)       # remove single-bold

        cleaned.append(s)

    digest_text = "\n".join(cleaned).strip()

    print(f"✅ Digest generated ({len(digest_text)} characters)")

    # --- Chunking for Slack (safe length per block) ---
    max_len = 2800
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📰 AI/Tech Daily Digest — {today}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"👋 <@{SLACK_USER_ID}> Your daily AI digest is ready!"}
        },
        {"type": "divider"}
    ]

    if len(digest_text) <= max_len:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": digest_text}})
    else:
        # split on double newlines (between sections)
        chunk = ""
        for para in digest_text.split("\n\n"):
            if len(chunk) + len(para) + 2 > max_len:
                if chunk:
                    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk.strip()}})
                    blocks.append({"type": "divider"})
                chunk = para + "\n\n"
            else:
                chunk += para + "\n\n"
        if chunk:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk.strip()}})

    # Footer
    blocks += [
        {"type": "divider"},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"_Powered by Gemini • Generated at {current_time}_"}
        ]}
    ]

    # Safety: Slack max 50 blocks
    if len(blocks) > 50:
        blocks = blocks[:49] + [{
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "_(truncated to fit Slack limits)_"}]
        }]

    # --- Post to Slack (top-level text includes mention for push) ---
    payload = {
        "text": f"<@{SLACK_USER_ID}> AI/Tech Daily Digest — {today}",
        "blocks": blocks
    }

    print("📤 Posting to Slack...")
    res = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=30)
    print("Slack status:", res.status_code, "| body:", res.text)
    res.raise_for_status()
    print("✅ Successfully posted to Slack!")

except Exception as e:
    print("❌ Error:", e)
    import traceback; traceback.print_exc()
    try:
        requests.post(
            SLACK_WEBHOOK_URL,
            json={"text": f"⚠️ Daily Digest Failed: {e}"},
            timeout=30
        )
    except:
        pass
    raise

print("🎉 Done!")
