import os
import threading
import requests
from pyrogram import Client, filters
from flask import Flask

# Environment variables
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
BLOGGER_API_KEY = os.environ["BLOGGER_API_KEY"]
BLOG_ID = os.environ["BLOG_ID"]
PORT = int(os.environ.get("PORT", 8080))

# Initialize Pyrogram client (Telegram Bot)
app = Client("blogger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize Flask app
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🤖 Blogger Telegram Bot is running."

def format_html(title, body):
    return f"""
    <h2>{title}</h2>
    <p>{body}</p>
    <hr>
    <p><em>Posted via Telegram Blogger Bot</em></p>
    """

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
            message.reply("❌ Failed to post. Check API key and Blog ID.")

    except Exception as e:
        message.reply(f"❌ Error: {e}")

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    # Start Flask in a thread
    threading.Thread(target=run_flask).start()
    print("🤖 Blogger Bot is running with Flask web server...")
    # Run Pyrogram client (bot)
    app.run()
