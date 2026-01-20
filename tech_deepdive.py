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

print("🚀 Starting Weekly AI Production & Research Digest with Gemini...")
print(f"📅 Date: {today.isoformat()} ({day_of_week})")

# Model selection (in order of preference)
MODEL_CHOICES = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
selected_model = MODEL_CHOICES[0]
print(f"✅ Using model: {selected_model}")

prompt = f"""You are an expert AI/ML engineer who bridges research and production, creating a WEEKLY digest for {today.isoformat()} ({day_of_week}).

Create a PRODUCTION-HEAVY digest (60/40 split) focusing on:
1. Production blog posts showing REAL IMPLEMENTATIONS at scale (PRIMARY FOCUS - 60%)
2. Research papers with REAL-WORLD PRODUCTION IMPACT (40%)

This digest must help engineers understand what's actually working in production AND which research is worth paying attention to. Cover the PAST 7 DAYS.

YOU MUST CREATE EXACTLY 2 SECTIONS WITH EXACTLY THESE HEADERS (copy them exactly):

🏗️ *PRODUCTION & ENGINEERING*
🔬 *RESEARCH WITH IMPACT*

PRODUCTION SECTION COMES FIRST and should be MORE COMPREHENSIVE (4-5 items).
RESEARCH SECTION follows with focused, high-signal papers (2-3 items).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 1 - 🏗️ *PRODUCTION & ENGINEERING* (4-5 posts) — PRIMARY FOCUS

SOURCE REQUIREMENTS - Engineering blogs from:
- AI Labs: Anthropic, OpenAI, Google AI/DeepMind, Meta AI, Cohere, Mistral
- Big Tech: Netflix Tech, Uber Engineering, LinkedIn Engineering, Airbnb Engineering, Spotify Engineering, DoorDash Engineering
- ML Platforms: Weights & Biases, Databricks, Modal, Replicate, Together.ai, Anyscale, Run:ai
- Infrastructure: AWS ML Blog, Google Cloud AI, Azure AI

CONTENT FOCUS - Real-world implementation stories:
- Deployment patterns and architectures
- Scaling challenges and solutions
- Cost optimizations with specific numbers
- Real-world tradeoffs and lessons learned
- Production incidents and post-mortems
- MLOps and infrastructure decisions

FOR EACH POST INCLUDE:
- Company name
- Problem they solved
- Architecture/approach used
- Metrics/results (latency, cost savings, scale)
- Key lessons learned
- Link to original post if available

TAGS TO ADD: [MLOps] [Infrastructure] [Scaling] [Cost] [Reliability] [Monitoring] [RAG] [Agents] [Fine-tuning] [Serving]

BONUS: When a production post references specific research/papers they implemented, MENTION IT. This connects the dots between research and production.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 2 - 🔬 *RESEARCH WITH IMPACT* (2-3 papers) — HIGH-SIGNAL ONLY

SOURCE REQUIREMENTS:
- ArXiv, Papers with Code, NeurIPS, ICML, ACL, EMNLP, CVPR, ICLR proceedings
- ONLY papers from the past 7 days with code/implementations available

CONTENT FOCUS - Only include papers that solve REAL ENGINEERING PROBLEMS:
- Efficiency gains (faster inference, reduced memory, lower latency)
- Deployment innovations (quantization, distillation, edge deployment)
- Cost reduction techniques (fewer parameters, cheaper training)
- Scalability solutions (distributed training, serving at scale)
- Production-ready techniques (RAG improvements, agent reliability, tool use)

FOR EACH PAPER INCLUDE:
- Paper title (in quotes)
- Institution/authors
- Key innovation (what's new)
- Production relevance (why engineers should care NOW)
- Metrics/results if available
- Link to code/paper if available

TAGS TO ADD: [NLP] [CV] [MLOps] [Infrastructure] [RAG] [Agents] [Efficiency] [Quantization] [Fine-tuning] [Serving]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**FORMAT FOR EACH BULLET POINT:**
• "Title" [TAG1] [TAG2] - Brief description. Technical details in 2-3 sentences with specific metrics, architecture choices, and practical takeaways.

**EXAMPLE OUTPUT:**

🏗️ *PRODUCTION & ENGINEERING*

• Anthropic: "Building Reliable AI Agents" [Agents] [Reliability] - How Anthropic designs agents that fail gracefully. Architecture uses explicit state machines with rollback capabilities. Reduced agent failure rate from 23% to 4% in production. Key lesson: always design for partial failures.

• Netflix: "Scaling Recommendations with LLMs" [Scaling] [RAG] - Netflix replaced embeddings with LLM-generated explanations. Hybrid architecture serves 200M users with p99 latency under 100ms. Cost optimization: cache common query patterns, reducing LLM calls by 60%.

• Uber: "Real-time Feature Store at Scale" [Infrastructure] [MLOps] - Uber rebuilt their feature store to handle 10M QPS with sub-10ms latency. Key insight: separate hot/cold storage tiers reduced costs by 40% while improving p99 latency.

• Modal: "Serverless GPU Inference Patterns" [Serving] [Cost] - How Modal optimizes cold starts for GPU workloads. Achieved 2-second cold starts for 70B models using checkpoint streaming. Shares patterns for batching and autoscaling.

🔬 *RESEARCH WITH IMPACT*

• "Speculative Decoding for LLM Inference" [Efficiency] [Serving] - Google Research paper achieves 2-3x inference speedup without quality loss. Uses small draft model to propose tokens, verified by large model in parallel. Production-ready technique already deployed in vLLM and TensorRT-LLM.

• "LoRA Land: Fine-tuning with 310 Adapters" [Fine-tuning] [Efficiency] - Stanford study shows LoRA matches full fine-tuning at 10% cost. Tested across 310 tasks with consistent results. Key insight: rank-16 sufficient for most production use cases.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL RULES:
1. PRODUCTION FIRST: 🏗️ section comes first with 4-5 items (60%)
2. RESEARCH SECOND: 🔬 section follows with 2-3 items (40%)
3. NO bold (**) in bullet points - only plain text
4. Section headers use single asterisks: 🏗️ *PRODUCTION & ENGINEERING*
5. Start IMMEDIATELY with production section - no introduction
6. End IMMEDIATELY after research section - no conclusion
7. Include BOTH sections - do not skip any
8. Add 1-2 relevant tags per item in square brackets
9. Focus on ACTIONABLE insights engineers can apply
10. Include specific metrics, numbers, and results where available
11. Prioritize RECENT content from the past 7 days
12. When production posts reference research papers, MENTION the connection

Begin with the production section now:"""

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

        # Check if both sections are present
        section_headers = [
            '🏗️',  # Production & Engineering
            '🔬',  # Research with Impact
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
            print("✅ Both sections found!")
        
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
section_emoji = ['🏗️', '🔬']

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
        "text": {"type": "plain_text", "text": f"🏗️ Weekly AI Production & Research Digest — {today.isoformat()}"}
    },
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"👋 <@{SLACK_USER_ID}> Your weekly digest is ready!\n🏗️ *Focus:* Production implementations (60%) + Impactful research (40%)\n📅 *Coverage:* Past 7 days of AI developments"}
    },
    {"type": "divider"}
]

if len(digest_text) <= max_len:
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": digest_text}})
else:
    print(f"⚠️  Content too long ({len(digest_text)} chars), splitting...")
    chunk = ""
    chunk_count = 0
    min_chunk_len = 100  # Minimum chunk size to avoid invalid blocks

    for para in digest_text.split("\n\n"):
        if len(chunk) + len(para) + 2 > max_len and len(chunk) >= min_chunk_len:
            chunk_count += 1
            print(f"   Chunk {chunk_count}: {len(chunk)} chars")
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk.strip()}})
            blocks.append({"type": "divider"})
            chunk = para + "\n\n"
        else:
            chunk += para + "\n\n"
    if chunk.strip():
        chunk_count += 1
        print(f"   Chunk {chunk_count}: {len(chunk)} chars")
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk.strip()}})

# Footer
blocks += [
    {"type": "divider"},
    {"type": "context", "elements": [
        {"type": "mrkdwn", "text": f"_Powered by Gemini • {current_time} • Weekly Production & Research Digest: Every Wednesday_"}
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
    "text": f"<@{SLACK_USER_ID}> Weekly AI Production & Research Digest — {today.isoformat()}",
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