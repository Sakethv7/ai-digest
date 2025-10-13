import os
import datetime as dt
from dateutil import tz
import requests
import google.generativeai as genai

# Configuration
TIMEZONE = "America/New_York"
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]  # Add this to GitHub secrets
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

today = dt.datetime.now(tz.gettz(TIMEZONE)).date().isoformat()
current_time = dt.datetime.now(tz.gettz(TIMEZONE)).strftime('%I:%M %p %Z')

print("🚀 Starting AI News Digest with Gemini...")
print(f"📅 Date: {today}")

# Create the model with Google Search grounding
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash-latest',
    tools='google_search_retrieval'  # This enables web search!
)

prompt = f"""You are an expert AI/tech news editor creating today's digest for {today} ({TIMEZONE}).

**Task:** Search the web and create a comprehensive daily digest of AI and tech news from the LAST 24-48 HOURS.

**Required Sections:**
1. 🔬 **Research & Models** - New AI research, papers, open-source LLMs
2. ⚖️ **Policy & Regulation** - AI laws, government actions, compliance news
3. 💻 **Hardware & Chips** - NVIDIA, AMD, TSMC, Intel, AI accelerators
4. 🚀 **Product Launches** - OpenAI, Google, Microsoft, Anthropic, Meta releases
5. 🎯 **Industry News** - Funding, acquisitions, partnerships, wild cards

**Format Requirements:**
- Each section: 2-4 items (10-15 items total)
- Each item: **Bold headline** + 1-2 sentence summary
- Include source links in markdown: [Source Name](url)
- Use bullet points (•) for items
- Be concise but informative

**Focus on:**
- Breaking news from today or yesterday
- Significant announcements and developments
- Credible sources (tech publications, official announcements)
- Accurate, factual information with citations

Search the web now and create the digest:"""

try:
    print("🔍 Searching the web and generating digest...")
    
    # Generate content with web search
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=3000,
        )
    )
    
    digest_text = response.text.strip()
    
    print(f"✅ Digest generated ({len(digest_text)} characters)")
    
    # Check if we got grounding metadata (sources used)
    if hasattr(response, 'grounding_metadata') and response.grounding_metadata:
        num_sources = len(response.grounding_metadata.grounding_chunks) if hasattr(response.grounding_metadata, 'grounding_chunks') else 0
        print(f"📚 Used {num_sources} web sources")
    
    # Format for Slack
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📰 AI/Tech Daily Digest — {today}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": digest_text
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Powered by Gemini 1.5 + Google Search • Generated at {current_time}_"
                }
            ]
        }
    ]
    
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