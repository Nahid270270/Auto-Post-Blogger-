import os
import requests
from pyrogram import Client, filters

# Telegram Config
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Blogger Config
BLOG_ID = os.getenv("BLOG_ID")
ACCESS_TOKEN = os.getenv("BLOGGER_ACCESS_TOKEN")  # OAuth 2.0 token

app = Client("blogposter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Blogger Post Function
def post_to_blogger(title, content):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    post_data = {
        "kind": "blogger#post",
        "blog": {"id": BLOG_ID},
        "title": title,
        "content": content
    }
    response = requests.post(url, json=post_data, headers=headers)
    return response.ok

@app.on_message(filters.channel)
async def post_from_channel(client, message):
    if message.text:
        title = message.text.split("\n")[0][:100]  # Title: প্রথম লাইন বা 100 চর কম
        content = message.text.replace("\n", "<br>")  # HTML support
        success = post_to_blogger(title, content)
        if success:
            print("✅ Posted to Blogger!")
        else:
            print("❌ Failed to post!")

app.run()
