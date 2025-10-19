import os
import datetime as dt
from dateutil import tz
import requests
import google.generativeai as genai

# Configuration
TIMEZONE = "America/New_York"
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U07DZBQGXDK")  # Default to your ID

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

**Example Format:**
🇺🇸 **USA Tech & AI**

• OpenAI launches GPT-5 with multimodal capabilities - New model processes text, images, and audio simultaneously with 35% performance improvement over GPT-4.

• US Congress passes AI Safety Framework Act - Bipartisan legislation establishes federal oversight for high-risk AI systems and requires transparency in algorithmic decision-making.

🇮🇳 **India Tech & AI**

• Krutrim AI raises $75M Series A from Peak XV Partners - Bangalore-based startup building India-first LLM trained on 22 Indian languages for local market needs.

• Government launches National AI Mission with $1.2B budget - Initiative focuses on building computing infrastructure, developing local talent, and supporting AI startups across India.

**Guidelines:**
- Section headers: emoji + bold text (e.g., 🇺🇸 **USA Tech & AI**)
- Bullet points: plain text only, NO bold
- Focus on: policies, funding, products, initiatives, research
- Skip random European tech news unless it's major AI policy
- USA: Big tech + government initiatives
- India: Startups, government programs, academic research
- Global: China/Japan developments, EU AI regulations only
- Be specific: company names, funding amounts, numbers
- Professional, newsworthy tone
- NO introductions or conclusions

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
    
    # Remove bold from bullet points but keep section headers bold
    import re
    lines = digest_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # If line starts with emoji (section header), keep it as is
        if any(emoji in line[:5] for emoji in ['🇺🇸', '🇮🇳', '🌏', '💰', '🚀', '🎯']):
            cleaned_lines.append(line)
        # If line starts with bullet, remove any bold
        elif line.strip().startswith('•'):
            # Remove **text** patterns from bullet lines only
            line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
            line = re.sub(r'\*([^*]+)\*', r'\1', line)
            cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)
    
    digest_text = '\n'.join(cleaned_lines)
    
    # Remove intro/outro fluff - keep only content from first emoji onwards
    lines = digest_text.split('\n')
    cleaned_lines = []
    started = False
    
    for line in lines:
        # Start collecting when we hit first emoji section
        if any(emoji in line for emoji in ['🇺🇸', '🇮🇳', '🌏', '💰', '🚀', '🎯']):
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
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"👋 <@{SLACK_USER_ID}> Your daily AI digest is ready!"
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