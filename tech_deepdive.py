import os
import re
import datetime as dt
from dateutil import tz
import requests
import google.generativeai as genai

# Configuration
TIMEZONE = "America/New_York"
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL_LEARNING"]  # Different webhook for learning
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U07DZBQGXDK")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

today = dt.datetime.now(tz.gettz(TIMEZONE)).date()
day_of_week = today.strftime('%A')
current_time = dt.datetime.now(tz.gettz(TIMEZONE)).strftime('%I:%M %p %Z')

print("🚀 Starting AI Tech Deep Dive with Gemini...")
print(f"📅 Date: {today.isoformat()} ({day_of_week})")

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

prompt = f"""You are an expert AI/ML researcher and educator creating a technical deep dive digest for {today.isoformat()} ({day_of_week}).

**Task:** Create a comprehensive technical digest covering open source AI, new techniques, research papers, and learning resources from the past 3-4 days.

This is a TECHNICAL digest - focus on HOW things work, new methodologies, open source tools, and educational content. Skip corporate news and funding.

**Required Sections (IN THIS ORDER):**

1. 🔬 Research Papers & Breakthroughs
   - Recent arXiv papers on AI/ML/DL
   - Novel techniques, architectures, algorithms
   - Academic research from universities worldwide
   - Benchmark improvements, new datasets

2. 🛠️ Open Source AI Projects
   - New open source LLMs, models, frameworks
   - Cool GitHub projects gaining traction
   - Community-built tools and libraries
   - Hugging Face releases, model cards

3. 💡 Techniques & Methods
   - New training techniques (LoRA, QLoRA, RLHF variants)
   - Prompt engineering breakthroughs
   - RAG improvements, vector DB innovations
   - Agentic AI frameworks and patterns
   - Semantic search advancements

4. 🖥️ AI Infrastructure & Chips
   - GPU/TPU developments
   - Edge AI, on-device models
   - Quantization techniques (GGUF, GPTQ, etc.)
   - Inference optimization
   - Local LLM running (Ollama, LM Studio updates)

5. 📚 Learning Resources
   - New courses, tutorials, guides
   - Technical blog posts worth reading
   - YouTube channels/videos explaining concepts
   - Books, papers with code implementations

6. 🔧 Tools & Software Updates
   - New releases of AI/ML tools and frameworks
   - IDE plugins, extensions, integrations
   - CLI tools, notebooks, debugging tools
   - Developer productivity tools for AI work

**Format Requirements:**
- Section headers: emoji + *Header Text* (single asterisks)
- Each bullet: Plain headline - Technical description
- NO bold in bullet points
- Use bullets (•) only
- 3-4 items per section (18-24 total)
- Each item: 2-3 sentences with TECHNICAL DETAILS

**Example Format:**
🔬 *Research Papers & Breakthroughs*

• "FlashAttention-3" achieves 2x speedup for long context - New paper from Stanford introduces optimized attention mechanism using GPU memory hierarchy. Enables 100K token context windows with minimal memory overhead. Code and benchmarks available on GitHub.

• Self-supervised learning breakthrough for multimodal models - Researchers combine CLIP-style contrastive learning with masked prediction to create models that learn from unlabeled video data. Achieves 95% of supervised performance with 10x less labeled data.

🛠️ *Open Source AI Projects*

• Nous Research releases "Hermes 3" - 405B parameter model with function calling - Open source LLM fine-tuned on Llama 3.1 base with advanced tool use capabilities. Outperforms GPT-4 on coding benchmarks. Available in GGUF format for local deployment.

• New vector database "LanceDB" gains Python integration - Columnar vector storage optimized for AI workloads with native pandas support. 10x faster than Pinecone for similarity search on embeddings. Fully local, no API needed.

**CRITICAL REQUIREMENTS:**
- You MUST include ALL 6 sections in your response. Do not skip any section.
- If you cannot find enough content for a section, create plausible technical examples based on current trends.
- Each section must have 3-4 bullet points.

**Guidelines:**
- Focus on TECHNICAL CONTENT - how things work, not who built it
- Include GitHub links, paper names, specific techniques
- Open source tools: licensing, model sizes, quantization formats
- Research: methodology, results, datasets used
- Techniques: explain the approach, advantages, use cases
- Learning: difficulty level, prerequisites, time investment
- Professional but accessible tone
- Skip all corporate funding/business news
- NO introductions - jump straight to technical content

Create the tech deep dive now:"""

try:
    print("🤖 Generating tech deep dive...")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=3500,
        ),
    )
    digest_text = (response.text or "").strip()

    # --- Normalize formatting for Slack ---
    digest_text = digest_text.replace('---', '').replace('##', '').replace('###', '')

    lines = digest_text.splitlines()
    cleaned = []
    section_emoji = ['🔬', '🛠️', '💡', '🖥️', '📚', '🔧']  # Fixed: Changed 🎯 to 🔧

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
            "text": {"type": "plain_text", "text": f"🔬 AI Tech Deep Dive — {today.isoformat()}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"👋 <@{SLACK_USER_ID}> Your tech deep dive is ready!\n🛠️ *Focus:* Open source, research, techniques & learning"}
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
            {"type": "mrkdwn", "text": f"_Powered by Gemini • {current_time} • Tech Deep Dive: Tue & Fri_"}
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
        "text": f"<@{SLACK_USER_ID}> AI Tech Deep Dive — {today.isoformat()}",
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