# ✅ Blogger Auto Post Bot
# ✅ Requires: Pyrogram, requests, python-dotenv

from pyrogram import Client, filters
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BLOGGER_API_KEY = os.getenv("BLOGGER_API_KEY")
BLOG_ID = os.getenv("BLOG_ID")

app = Client("blogger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ✅ Simple HTML template for blog posts
def format_html(title, body):
    return f"""
    <h2>{title}</h2>
    <p>{body}</p>
    <hr>
    <p><em>Posted via Telegram Blogger Bot</em></p>
    """

# ✅ Function to publish post to Blogger
def publish_to_blogger(title, content):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/?key={BLOGGER_API_KEY}"
    data = {
        "kind": "blogger#post",
        "blog": {"id": BLOG_ID},
        "title": title,
        "content": content
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=data, headers=headers)
    return response.status_code == 200

# ✅ Command: /post Title | Content
@app.on_message(filters.command("post") & filters.private)
def post_to_blog(client, message):
    try:
        if "|" not in message.text:
            return message.reply("⚠️ Use format: /post Title | Content")

        raw = message.text.split("/post", 1)[1].strip()
        title, body = [x.strip() for x in raw.split("|", 1)]
        html = format_html(title, body)

        sent = publish_to_blogger(title, html)
        if sent:
            message.reply("✅ Posted to Blogger!")
        else:
            message.reply("❌ Failed to post. Check your API key and Blog ID.")

    except Exception as e:
        message.reply(f"❌ Error: {e}")

print("🤖 Blogger Bot is running...")
app.run()
