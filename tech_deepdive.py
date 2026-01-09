import os
import re
import datetime as dt
from dateutil import tz
import requests
from google import genai

# Configuration
TIMEZONE = "America/New_York"
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL_LEARNING"]  # Different webhook for learning
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U07DZBQGXDK")

# Configure Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

today = dt.datetime.now(tz.gettz(TIMEZONE)).date()
day_of_week = today.strftime('%A')
current_time = dt.datetime.now(tz.gettz(TIMEZONE)).strftime('%I:%M %p %Z')

print("🚀 Starting Weekly AI Tech Deep Dive with Gemini...")
print(f"📅 Date: {today.isoformat()} ({day_of_week})")

# Model selection (in order of preference)
MODEL_CHOICES = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
selected_model = MODEL_CHOICES[0]
print(f"✅ Using model: {selected_model}")

prompt = f"""You are an expert AI/ML researcher and educator creating a comprehensive WEEKLY technical deep dive digest for {today.isoformat()} ({day_of_week}).

Create an in-depth technical digest covering the most significant open source AI developments, new techniques, research papers, and learning resources from the PAST 7 DAYS.

This is a WEEKLY TECHNICAL digest - be thorough and cover the MOST IMPORTANT developments of the entire week. Focus on HOW things work, new methodologies, open source tools, and educational content. Prioritize the most impactful and noteworthy items.

YOU MUST CREATE EXACTLY 6 SECTIONS WITH EXACTLY THESE HEADERS (copy them exactly):

🔬 *Research Papers & Breakthroughs*
🛠️ *Open Source AI Projects*
💡 *Techniques & Methods*
🖥️ *AI Infrastructure & Chips*
📚 *Learning Resources*
🔧 *Tools & Software Updates*

Each section MUST have 4-5 bullet points starting with • (this is a weekly digest, so be comprehensive)

Section 1 - 🔬 *Research Papers & Breakthroughs*
Cover: Recent arXiv papers, novel techniques, architectures, algorithms, academic research, benchmark improvements, new datasets

Section 2 - 🛠️ *Open Source AI Projects*
Cover: New open source LLMs/models/frameworks, GitHub projects, community tools/libraries, Hugging Face releases

Section 3 - 💡 *Techniques & Methods*
Cover: Training techniques (LoRA, QLoRA, RLHF), prompt engineering, RAG improvements, vector DB innovations, agentic AI frameworks

Section 4 - 🖥️ *AI Infrastructure & Chips*
Cover: GPU/TPU developments, edge AI, quantization techniques (GGUF, GPTQ), inference optimization, local LLM running (Ollama, LM Studio)

Section 5 - 📚 *Learning Resources*
Cover: New courses, tutorials, guides, technical blog posts, YouTube videos/channels, books, papers with code

Section 6 - 🔧 *Tools & Software Updates*
Cover: New releases of AI/ML tools/frameworks, IDE plugins/extensions, CLI tools, notebooks, debugging tools, developer productivity tools

**Format for each bullet point:**
• "Headline or tool name" - brief description - Technical details in 2-3 sentences. Include specifics like model sizes, performance metrics, GitHub repos, techniques used.

**Example:**
🔬 *Research Papers & Breakthroughs*

• "FlashAttention-3" achieves 2x speedup for long context - New paper from Stanford introduces optimized attention mechanism using GPU memory hierarchy. Enables 100K token context windows with minimal memory overhead. Code and benchmarks available on GitHub.

• Self-supervised learning breakthrough for multimodal models - Researchers combine CLIP-style contrastive learning with masked prediction to create models that learn from unlabeled video data. Achieves 95% of supervised performance with 10x less labeled data.

🛠️ *Open Source AI Projects*

• Nous Research releases "Hermes 3" - Open source 405B parameter model fine-tuned on Llama 3.1 base with advanced function calling. Outperforms GPT-4 on coding benchmarks. Available in GGUF format for local deployment.

IMPORTANT RULES:
1. NO bold (**) in bullet points - only plain text
2. Section headers use single asterisks: 🔬 *Research Papers & Breakthroughs*
3. Start IMMEDIATELY with first section - no introduction
4. End IMMEDIATELY after last section - no conclusion
5. Include ALL 6 sections - do not skip any
6. Focus on technical details, not corporate news
7. 4-5 items per section (24-30 items total) - this is a WEEKLY digest, be comprehensive
8. Prioritize the most significant and impactful developments from the entire week

Begin with the first section now:"""

max_retries = 3
for attempt in range(max_retries):
    try:
        print(f"🤖 Generating tech deep dive (attempt {attempt + 1}/{max_retries})...")
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=6000,
            ),
        )
        digest_text = (response.text or "").strip()

        # Check if all 6 sections are present
        section_headers = [
            '🔬',  # Research Papers
            '🛠️',  # Open Source
            '💡',  # Techniques
            '🖥️',  # Infrastructure
            '📚',  # Learning
            '🔧'   # Tools
        ]
        
        missing_sections = [emoji for emoji in section_headers if emoji not in digest_text]
        
        if missing_sections:
            print(f"⚠️  Missing sections: {missing_sections}")
            if attempt < max_retries - 1:
                print("   Retrying...")
                continue
            else:
                print("   Proceeding anyway (max retries reached)")
        else:
            print("✅ All 6 sections found!")
        
        break  # Success, exit retry loop
        
    except Exception as e:
        if attempt < max_retries - 1:
            print(f"⚠️  Generation error: {e}. Retrying...")
            continue
        else:
            raise

# --- Normalize formatting for Slack ---
digest_text = digest_text.replace('---', '').replace('##', '').replace('###', '')

lines = digest_text.splitlines()
cleaned = []
section_emoji = ['🔬', '🛠️', '💡', '🖥️', '📚', '🔧']

for line in lines:
    s = line.strip()
    
    if not s:
        cleaned.append(s)
        continue
        
    # For section headers, ensure single asterisks
    if any(e in s for e in section_emoji):
        s = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', s)
        if '*' not in s:
            parts = s.split(' ', 1)
            if len(parts) == 2:
                s = f"{parts[0]} *{parts[1]}*"
        cleaned.append(s)
        continue

    # For bullets, strip bold/italic
    if s.startswith('•'):
        s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)
        s = re.sub(r'\*([^*]+)\*', r'\1', s)
        cleaned.append(s)
        continue
        
    cleaned.append(s)

digest_text = "\n".join(cleaned).strip()

# Remove intro/outro
lines = digest_text.split('\n')
started = False
final_lines = []
for line in lines:
    if not started and any(e in line for e in section_emoji):
        started = True
    if started:
        final_lines.append(line)

digest_text = '\n'.join(final_lines).strip()

print(f"✅ Tech deep dive generated ({len(digest_text)} characters)")

# --- Chunking for Slack ---
max_len = 2800
blocks = [
    {
        "type": "header",
        "text": {"type": "plain_text", "text": f"🔬 Weekly AI Tech Deep Dive — {today.isoformat()}"}
    },
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"👋 <@{SLACK_USER_ID}> Your weekly tech deep dive is ready!\n🛠️ *Focus:* Open source, research, techniques & learning\n📅 *Coverage:* Past 7 days of AI developments"}
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
        {"type": "mrkdwn", "text": f"_Powered by Gemini • {current_time} • Weekly Tech Deep Dive: Every Wednesday_"}
    ]}
]

# Safety: Slack max 50 blocks
if len(blocks) > 50:
    print(f"⚠️  Too many blocks ({len(blocks)}), truncating to 50")
    blocks = blocks[:49] + [{
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "_(truncated)_"}]
    }]

# --- Post to Slack ---
payload = {
    "text": f"<@{SLACK_USER_ID}> Weekly AI Tech Deep Dive — {today.isoformat()}",
    "blocks": blocks
}

print(f"📤 Posting to Slack... ({len(blocks)} blocks)")
try:
    res = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=30)
    print(f"   Response: {res.status_code} | {res.text[:200]}")
    res.raise_for_status()
    print("✅ Successfully posted to Slack!")
except Exception as e:
    print(f"❌ Error posting to Slack: {e}")
    import traceback
    traceback.print_exc()
    
    try:
        requests.post(
            SLACK_WEBHOOK_URL,
            json={
                "text": f"⚠️ Tech Deep Dive Failed",
                "blocks": [{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Error:*\n```{str(e)[:500]}```"}
                }]
            },
            timeout=30
        )
    except:
        pass
    raise

print("🎉 Done!")