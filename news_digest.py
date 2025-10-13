import os
import datetime as dt
from dateutil import tz
import requests
from openai import OpenAI

# Configuration
MODEL = "gpt-4-turbo-preview"
TIMEZONE = "America/New_York"
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)
today = dt.datetime.now(tz.gettz(TIMEZONE)).date()
yesterday = today - dt.timedelta(days=7)  # Changed from 2 to 7 days

# Fetch real news from NewsAPI
def fetch_ai_news():
    """Fetch AI-related news from the last 7 days"""
    
    queries = [
        "artificial intelligence",
        "OpenAI OR Anthropic OR Google AI",
        "AI regulation OR AI policy",
        "NVIDIA OR AMD AI chips",
        "large language model OR LLM"
    ]
    
    all_articles = []
    
    for query in queries:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": yesterday.isoformat(),
            "to": today.isoformat(),
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 20,
            "apiKey": NEWSAPI_KEY
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "ok":
                articles_found = data.get("articles", [])
                print(f"  ✓ '{query}': found {len(articles_found)} articles")
                all_articles.extend(articles_found)
            else:
                print(f"  ✗ '{query}': status={data.get('status')}, message={data.get('message', 'N/A')}")
        except Exception as e:
            print(f"  ✗ Error fetching '{query}': {e}")
    
    # Remove duplicates by URL
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        url = article.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    return unique_articles[:30]

# Fetch news
print("📡 Fetching latest AI news...")
articles = fetch_ai_news()
print(f"✅ Found {len(articles)} articles")

if not articles:
    print("⚠️  No articles found. Exiting.")
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠️ *No AI news found for {today.isoformat()}*"
            }
        }
    ]
    requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks}, timeout=30)
    exit(0)

# Prepare context for GPT
news_context = "\n\n".join([
    f"**{art['title']}**\n{art.get('description', 'No description')}\nSource: {art['source']['name']}\nURL: {art['url']}\nPublished: {art['publishedAt']}"
    for art in articles
])

prompt = f"""You are a news desk editor creating a daily AI/tech digest for {today.isoformat()} ({TIMEZONE}).

Here are the latest news articles from the past week:

{news_context}

**Your task:**
Create a concise, well-organized Slack digest with:

**Structure:**
- 3-5 sections (e.g., Research, Policy & Regulation, Hardware/Chips, Product Launches, Industry News)
- 10-14 of the MOST IMPORTANT and RECENT items
- Each item: **Bold headline** + 1-sentence takeaway + [link](url)

**Guidelines:**
- Prioritize the most recent articles (last 24-48 hours if available)
- Focus on significant developments only
- Group related stories together
- Include the actual links from the articles
- Use Markdown formatting for Slack
- Make it scannable and informative

Create the digest now:"""

try:
    # Generate digest with GPT
    print("🤖 Generating digest with GPT-4...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are an expert tech news editor specializing in AI."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=2500
    )
    
    # FIXED: Correct way to extract content from the response
    digest_md = response.choices[0].message.content.strip()
    
    # Format for Slack
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📰 AI/Tech Daily Digest — {today.isoformat()}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": digest_md
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Generated from {len(articles)} articles • {dt.datetime.now(tz.gettz(TIMEZONE)).strftime('%I:%M %p %Z')}_"
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
    
    print(f"✅ Successfully posted to Slack!")
    print(f"📊 Articles processed: {len(articles)}")
    print(f"📝 Digest length: {len(digest_md)} characters")
    
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
    requests.post(SLACK_WEBHOOK_URL, json={"blocks": error_blocks}, timeout=30)
    raise