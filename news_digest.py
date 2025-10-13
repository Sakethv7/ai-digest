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

# Use the standard Gemini model (free tier compatible)
# Try models in order of preference
model = None
model_names = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']

for model_name in model_names:
    try:
        model = genai.GenerativeModel(model_name)
        print(f"✅ Using model: {model_name}")
        break
    except Exception as e:
        print(f"⚠️  {model_name} not available: {e}")
        continue

if model is None:
    error_msg = "Could not initialize any Gemini model"
    print(f"❌ {error_msg}")
    # Post error to Slack and exit
    error_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⚠️ Daily Digest Failed - Model Unavailable"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Tried models: {', '.join(model_names)}\n\nNo compatible models available on free tier."
            }
        }
    ]
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"blocks": error_blocks}, timeout=30)
    except:
        pass
    raise RuntimeError(error_msg)

prompt = f"""You are an expert AI/tech news editor creating today's digest for {today}.

Create a comprehensive daily AI/tech digest with the following sections:

1. 🔬 Research & Models
2. ⚖️ Policy & Regulation  
3. 💻 Hardware & Chips
4. 🚀 Product & Industry
5. 🎯 Emerging Trends

FORMAT REQUIREMENTS (CRITICAL):
- Each section should have 2-3 news items
- Format each item as: *Headline* followed by 1-2 sentences of explanation
- Use • bullets for each item
- Do NOT use ** or ### markdown - use *text* for bold instead
- Keep headlines concise and punchy
- Be specific about companies, models, and technologies

Example format:
🔬 *Research & Models*

• *OpenAI Releases GPT-5* OpenAI has launched its latest model with enhanced reasoning capabilities. The model shows significant improvements in mathematical and coding tasks.

• *Anthropic Announces Claude 4* The new model features extended context windows and improved safety measures. Early benchmarks show strong performance across multiple domains.

Generate the digest now with realistic, specific AI/tech developments:"""

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
    
    # Split into sections for better Slack rendering
    sections = []
    current_section = ""
    
    for line in digest_text.split('\n'):
        line_stripped = line.strip()
        
        # Check if this is a section header (emoji at start)
        if line_stripped and line_stripped[0] in ['🔬', '⚖️', '💻', '🚀', '🎯']:
            if current_section:
                sections.append(current_section.strip())
            current_section = line + '\n'
        else:
            current_section += line + '\n'
    
    if current_section:
        sections.append(current_section.strip())
    
    # Build Slack blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📰 AI/Tech Daily Digest",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📅 {dt.datetime.now(tz.gettz(TIMEZONE)).strftime('%A, %B %d, %Y')}"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]
    
    # Add each section as a separate block
    for section in sections:
        if section.strip():
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": section
                }
            })
    
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
                    "text": f"🤖 _Powered by Gemini 2.5 Flash • Generated at {current_time}_"
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
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⚠️ Daily Digest Failed"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{str(e)}```"
            }
        }
    ]
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"blocks": error_blocks}, timeout=30)
    except:
        pass
    raise

print("🎉 Done!")