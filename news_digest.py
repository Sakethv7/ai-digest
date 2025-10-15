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

**Task:** Create a comprehensive daily digest with SEPARATE sections for USA, India, and global coverage.

**Required Sections (IN THIS ORDER):**

1. 🇺🇸 **USA Tech & AI** - American companies, Silicon Valley, US policy, major announcements
2. 🇮🇳 **India Tech & AI** - Indian startups, government initiatives, local developments, funding
3. 🌏 **Global Tech News** - China, Japan, EU, Southeast Asia, rest of world
4. 🔬 **Research & Models** - New AI models, research breakthroughs, papers (any country)
5. 💻 **Hardware & Chips** - NVIDIA, AMD, TSMC, Intel, chip developments globally
6. 🚀 **Product Launches** - New AI products, features, services worldwide
7. 💰 **Funding & M&A** - Major deals, IPOs, acquisitions, partnerships
8. 🎯 **Wild Cards** - Breakthroughs, controversies, emerging trends

**Format Requirements:**
- Use bullet points (•) NOT numbered lists
- Each item: **Bold headline** followed by 1-2 sentence description
- NO ## markdown headers or ### - use emoji + **Bold Section Names** only
- Keep sections clean and scannable
- 2-3 items per section (16-24 items total)

**Example Format:**
🇺🇸 **USA Tech & AI**

• **OpenAI releases GPT-5 with breakthrough reasoning**: Latest model shows unprecedented capabilities in complex problem-solving. Early tests show 40% improvement in coding and math tasks.

• **US Senate passes AI Safety Act with bipartisan support**: New legislation establishes federal framework for AI regulation. Bill includes provisions for algorithmic transparency and liability.

🇮🇳 **India Tech & AI**

• **Ola founder launches new AI startup with $50M funding**: Bhavish Aggarwal unveils Krutrim AI, India's first homegrown LLM. Model trained on 20+ Indian languages including Hindi, Tamil, Telugu.

• **IIT Madras develops low-cost AI chip for edge computing**: Indian researchers create affordable AI accelerator for rural healthcare. Chip costs under $10 and runs on solar power.

**Guidelines:**
- Be specific with company names, numbers, and locations
- USA and India sections should have DOMESTIC news from those countries
- Global section covers REST OF WORLD (China, Japan, EU, etc.)
- Professional tone, no fluff
- NO introductory paragraphs - jump straight into sections
- Make items newsworthy and realistic

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
    
    # Clean up unwanted markdown formatting
    digest_text = digest_text.replace('##', '')
    digest_text = digest_text.replace('###', '')
    digest_text = digest_text.replace('---', '')
    
    # Remove intro/outro fluff - keep only content from first emoji onwards
    lines = digest_text.split('\n')
    cleaned_lines = []
    started = False
    
    for line in lines:
        # Start collecting when we hit first emoji section
        if any(emoji in line for emoji in ['🇺🇸', '🇮🇳', '🌏', '🔬', '💻', '🚀', '💰', '🎯']):
            started = True
        
        if started:
            cleaned_lines.append(line)
    
    digest_text = '\n'.join(cleaned_lines).strip()
    
    print(f"✅ Digest generated ({len(digest_text)} characters)")
    
    # Split digest into manageable chunks for Slack (max 3000 chars per block)
    max_length = 2800
    
    digest_blocks = []
    
    if len(digest_text) <= max_length:
        # Short enough - use single block
        digest_blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": digest_text
            }
        })
    else:
        # Too long - split intelligently
        print(f"⚠️  Digest too long ({len(digest_text)} chars), splitting...")
        
        # Split by double newlines (paragraphs/sections)
        chunks = []
        current_chunk = ""
        
        for paragraph in digest_text.split('\n\n'):
            # If adding this paragraph would exceed limit, start new chunk
            if len(current_chunk) + len(paragraph) + 2 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + '\n\n'
            else:
                current_chunk += paragraph + '\n\n'
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        print(f"📦 Split into {len(chunks)} chunks")
        
        # Create blocks for each chunk
        for i, chunk in enumerate(chunks):
            if chunk:
                print(f"   Chunk {i+1}: {len(chunk)} chars")
                digest_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": chunk
                    }
                })
                # Add divider between chunks (except after last one)
                if i < len(chunks) - 1:
                    digest_blocks.append({"type": "divider"})
    
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
    print(f"   Total blocks: {len(blocks)}")
    
    # Slack has a limit of 50 blocks per message
    if len(blocks) > 50:
        print(f"⚠️  Too many blocks ({len(blocks)}), truncating to 50")
        blocks = blocks[:49]
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": "_Content truncated due to length..._"
            }]
        })
    
    try:
        res = requests.post(
            SLACK_WEBHOOK_URL,
            json={"blocks": blocks},
            timeout=30
        )
        res.raise_for_status()
        print("✅ Successfully posted to Slack!")
    except requests.exceptions.HTTPError as e:
        print(f"❌ Slack API error: {e}")
        print(f"   Response: {res.text}")
        
        # Fallback: Send simplified version
        print("📤 Trying simplified fallback message...")
        fallback_blocks = [
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
                    "text": f"Generated a {len(digest_text)} character digest, but encountered formatting issues. Check GitHub Actions logs for full content."
                }
            }
        ]
        res2 = requests.post(SLACK_WEBHOOK_URL, json={"blocks": fallback_blocks}, timeout=30)
        res2.raise_for_status()
        print("✅ Fallback message posted")
        
        # Print the full digest to logs so you can see it
        print("\n" + "="*80)
        print("FULL DIGEST CONTENT:")
        print("="*80)
        print(digest_text)
        print("="*80 + "\n")
        raise
    
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