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
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U07DZBQGXDK")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

today = dt.datetime.now(tz.gettz(TIMEZONE)).date()
day_of_week = today.strftime('%A')
current_time = dt.datetime.now(tz.gettz(TIMEZONE)).strftime('%I:%M %p %Z')

# Determine the period we're covering
if day_of_week == 'Monday':
    period = "Past Week (Thu-Sun)"
    days_covered = "4 days"
elif day_of_week == 'Thursday':
    period = "Mid-Week (Mon-Wed)"
    days_covered = "3 days"
else:
    period = "Recent Days"
    days_covered = "recent days"

print("🚀 Starting AI Weekly Digest with Gemini...")
print(f"📅 Date: {today.isoformat()} ({day_of_week})")
print(f"📊 Period: {period}")

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
for name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]:
    try:
        model = genai.GenerativeModel(name)
        print(f"✅ Using model: {name}")
        break
    except Exception as e:
        print(f"⚠️  {name} not available: {e}")
if model is None:
    raise SystemExit("No Gemini model available")

prompt = f"""You are an expert AI/tech news editor creating a weekly summary digest for {today.isoformat()} ({day_of_week}).

**Task:** Create a comprehensive WEEKLY SUMMARY covering the {period} ({days_covered} of news).

This is NOT a daily digest - combine and summarize the most important developments from the entire period.

**Required Sections (IN THIS ORDER):**

1. 🇺🇸 USA Tech & AI
   - Major AI company announcements (OpenAI, Google, Microsoft, Anthropic, Meta)
   - US government policies, regulations, funding initiatives
   - Significant product launches, models, breakthroughs

2. 🇮🇳 India Tech & AI
   - Indian AI startups and major developments
   - Government initiatives and policy changes
   - Significant funding rounds (>$20M), product launches
   - IIT/academic research highlights

3. 🌏 Global AI News
   - China AI developments (Baidu, Alibaba, etc.)
   - Japan tech initiatives
   - EU AI policies and major regulatory updates
   - International partnerships

4. 💰 Funding & M&A
   - Major funding rounds (>$50M preferred)
   - Notable acquisitions, IPOs
   - Strategic investments in AI/tech

5. 🚀 Product Launches
   - Significant new AI products, features, tools
   - Major software/hardware releases
   - Game-changing launches only

6. 🎯 Key Insights
   - Most important trends from the period
   - Notable breakthroughs or policy shifts
   - What to watch next

**Format Requirements:**
- Section headers: emoji + *Header Text* (single asterisks for bold in Slack)
- Each bullet: Plain headline - Concise description
- NO bold in bullet points
- Use bullets (•) only
- 3-4 items per section (18-24 total)
- Each item: 2-3 sentences with key details

**Example Format:**
🇺🇸 *USA Tech & AI*

• OpenAI releases GPT-5 with breakthrough multimodal reasoning - New flagship model demonstrates 40% improvement in complex tasks across text, image, and video. Early enterprise beta shows significant gains in coding, analysis, and creative work. Pricing starts at $20/month for individual users.

• US Senate passes comprehensive AI Safety Framework Act - Landmark bipartisan legislation establishes federal oversight for high-risk AI systems including transparency requirements. Implementation begins Q1 2026 with initial focus on healthcare and financial services.

**Guidelines:**
- This is a WEEKLY SUMMARY - combine related stories
- Focus on IMPACT and KEY DETAILS
- Section headers: single asterisks *like this*
- Bullet points: plain text only
- Skip minor news - only include significant developments
- Include specific numbers: funding amounts, percentages, dates
- USA: Big tech + government
- India: Major startups, government programs
- Global: China/Japan developments, EU regulations
- Professional, analytical tone
- NO introductions - jump straight to content

Create the weekly digest now:"""

try:
    print("🤖 Generating weekly digest...")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.6,
            max_output_tokens=3500,
        ),
    )
    digest_text = (response.text or "").strip()

    # --- Normalize formatting for Slack ---
    # Remove markdown noise
    digest_text = digest_text.replace('---', '').replace('##', '').replace('###', '')

    lines = digest_text.splitlines()
    cleaned = []
    section_emoji = ['🇺🇸', '🇮🇳', '🌏', '💰', '🚀', '🎯']

    for line in lines:
        s = line.strip()
        
        # Skip empty lines or intro/outro fluff
        if not s:
            cleaned.append(s)
            continue
            
        # For section headers (with emoji), ensure single asterisks
        if any(e in s for e in section_emoji):
            # Convert **Header** → *Header* 
            s = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', s)
            # If no asterisks, add them
            if '*' not in s:
                parts = s.split(' ', 1)
                if len(parts) == 2:
                    s = f"{parts[0]} *{parts[1]}*"
            cleaned.append(s)
            continue

        # For bullet lines, strip ALL bold/italic formatting
        if s.startswith('•'):
            s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)  # remove **bold**
            s = re.sub(r'\*([^*]+)\*', r'\1', s)      # remove *italic*
            cleaned.append(s)
            continue
            
        # Other lines pass through
        cleaned.append(s)

    digest_text = "\n".join(cleaned).strip()

    # Remove any intro/outro paragraphs (keep only from first emoji onwards)
    lines = digest_text.split('\n')
    started = False
    final_lines = []
    for line in lines:
        if not started and any(e in line for e in section_emoji):
            started = True
        if started:
            final_lines.append(line)
    
    digest_text = '\n'.join(final_lines).strip()

    print(f"✅ Weekly digest generated ({len(digest_text)} characters)")

    # --- Chunking for Slack ---
    max_len = 2800
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📰 AI/Tech Weekly Digest — {today.isoformat()}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"👋 <@{SLACK_USER_ID}> Your weekly AI digest is ready!\n📊 *Covering:* {period}"}
        },
        {"type": "divider"}
    ]

    if len(digest_text) <= max_len:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": digest_text}})
    else:
        print(f"⚠️  Content too long ({len(digest_text)} chars), splitting...")
        chunk = ""
        chunk_count = 0
        for para in digest_text.split("\n\n"):
            if len(chunk) + len(para) + 2 > max_len:
                if chunk:
                    chunk_count += 1
                    print(f"   Chunk {chunk_count}: {len(chunk)} chars")
                    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk.strip()}})
                    blocks.append({"type": "divider"})
                chunk = para + "\n\n"
            else:
                chunk += para + "\n\n"
        if chunk:
            chunk_count += 1
            print(f"   Chunk {chunk_count}: {len(chunk)} chars")
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk.strip()}})

    # Footer
    blocks += [
        {"type": "divider"},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"_Powered by Gemini • {current_time} • Twice weekly: Mon & Thu_"}
        ]}
    ]

    # Safety: Slack max 50 blocks
    if len(blocks) > 50:
        print(f"⚠️  Too many blocks ({len(blocks)}), truncating to 50")
        blocks = blocks[:49] + [{
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "_(truncated to fit Slack limits)_"}]
        }]

    # --- Post to Slack ---
    payload = {
        "text": f"<@{SLACK_USER_ID}> AI/Tech Weekly Digest — {today.isoformat()} ({period})",
        "blocks": blocks
    }

    print(f"📤 Posting to Slack... ({len(blocks)} blocks)")
    res = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=30)
    print(f"   Response: {res.status_code} | {res.text[:200]}")
    res.raise_for_status()
    print("✅ Successfully posted to Slack!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    
    # Try to post error to Slack
    try:
        requests.post(
            SLACK_WEBHOOK_URL,
            json={
                "text": f"⚠️ Weekly Digest Failed",
                "blocks": [{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Error generating weekly digest:*\n```{str(e)[:500]}```"}
                }]
            },
            timeout=30
        )
    except:
        pass
    raise

print("🎉 Done!")