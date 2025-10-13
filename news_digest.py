import os
import datetime as dt
from dateutil import tz
import requests
import google.generativeai as genai

# Configuration
TIMEZONE = "America/New_York"
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

today = dt.datetime.now(tz.gettz(TIMEZONE)).date().isoformat()
current_time = dt.datetime.now(tz.gettz(TIMEZONE)).strftime('%I:%M %p %Z')

print("🚀 Starting AI News Digest with Gemini...")
print(f"📅 Date: {today}")

# List available models to debug
print("📋 Checking available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"  ✓ {m.name}")
except Exception as e:
    print(f"  ⚠️  Could not list models: {e}")

# Use the standard Gemini model
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    print("✅ Using model: gemini-2.5-flash")
except Exception as e:
    print(f"⚠️  gemini-2.5-flash not available, trying gemini-1.5-flash: {e}")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Using model: gemini-1.5-flash")
    except Exception as e2:
        print(f"⚠️  gemini-1.5-flash not available, trying gemini-pro: {e2}")
        model = genai.GenerativeModel('gemini-pro')
        print("✅ Using fallback model: gemini-pro")

prompt = f"""You are an expert AI/tech news editor creating today's digest for {today} ({TIMEZONE}).

**Task:** Based on your knowledge and recent trends in AI/tech, create a comprehensive daily digest that would typically be newsworthy.

**Required Sections:**
1. 🔬 **Research & Models** - AI research trends, LLM developments, notable papers
2. ⚖️ **Policy & Regulation** - AI governance, regulatory developments, standards
3. 💻 **Hardware & Chips** - AI accelerators, chip developments (NVIDIA, AMD, etc.)
4. 🚀 **Product & Industry** - Major AI product launches, startup news, partnerships
5. 🎯 **Emerging Trends** - Novel applications, safety discussions, wild cards

**Format Requirements:**
- Each section: 2-3 items (10-15 items total)
- Each item: **Bold headline** + 1-2 sentence insight
- Use bullet points (•) for items
- Be specific about companies, models, and developments
- Make it informative and engaging

**Guidelines:**
- Focus on significant, realistic developments in the AI space
- Include specific names of companies, models, and technologies
- Keep tone professional and factual
- Organize by importance within each section

Create the digest now:"""

try:
    print("🤖 Generating digest with Gemini...")
    
    # Generate content
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=3000,
        )
    )
    
    digest_text = response.text.strip()
    
    print(f"✅ Digest generated ({len(digest_text)} characters)")
    
    # Split digest if it's too long for Slack (max 3000 chars per block)
    max_length = 2900  # Leave some buffer
    
    if len(digest_text) <= max_length:
        # Short enough - use single block
        digest_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": digest_text
                }
            }
        ]
    else:
        # Too long - split into multiple blocks
        print(f"⚠️  Digest too long ({len(digest_text)} chars), splitting...")
        
        # Split by sections (look for section headers with emoji)
        sections = []
        current_section = ""
        
        for line in digest_text.split('\n'):
            if line.strip().startswith('**') and any(emoji in line for emoji in ['🔬', '⚖️', '💻', '🚀', '🎯']):
                # New section header found
                if current_section:
                    sections.append(current_section.strip())
                current_section = line + '\n'
            else:
                current_section += line + '\n'
        
        if current_section:
            sections.append(current_section.strip())
        
        # Create blocks for each section
        digest_blocks = []
        for section in sections:
            if section:
                digest_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": section
                    }
                })
    
    # Format for Slack
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📰 AI/Tech Daily Digest — {today}"
            }
        }
    ]
    
    # Add digest blocks
    blocks.extend(digest_blocks)
    
    # Add footer
    blocks.extend([
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Powered by Gemini 2.5 • Generated at {current_time}_"
                }
            ]
        }
    ])
    
    # Post to Slack
    print("📤 Posting to Slack...")
    res = requests.post(
        SLACK_WEBHOOK_URL,
        json={"blocks": blocks},
        timeout=30
    )
    res.raise_for_status()
    
    print("✅ Successfully posted to Slack!")
    print(f"📊 Final digest: {len(digest_text)} characters")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    
    # Post error to Slack
    error_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠️ *Daily Digest Failed*\n```{str(e)}```"
            }
        }
    ]
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"blocks": error_blocks}, timeout=30)
    except:
        pass
    raise

print("🎉 Done!")