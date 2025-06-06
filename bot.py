from pyrogram import Client, filters
import requests
import os

# 🔐 Load sensitive data from environment variables (server-based)
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
BLOGGER_API_KEY = os.environ["BLOGGER_API_KEY"]
BLOG_ID = os.environ["BLOG_ID"]

app = Client("blogger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def format_html(title, body):
    # HTML ফরম্যাটিং এখানে ঠিক আছে
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
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        # ডিবাগিং এর জন্য এই লাইনগুলো খুবই গুরুত্বপূর্ণ
        print(f"Blogger API Request URL: {url}")
        print(f"Blogger API Request Data: {data}")
        print(f"Blogger API Response Status: {response.status_code}")
        print(f"Blogger API Response Body: {response.text}")
        
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Network or request error: {e}")
        return False

@app.on_message(filters.command("post") & filters.private)
def post_to_blog(client, message):
    try:
        # নিশ্চিত করুন যে মেসেজে "/post" অংশটি আছে এবং তারপর "|" আছে
        if not message.text or not message.text.lower().startswith("/post"):
            return message.reply("⚠️ Use format: /post Title | Content")

        raw_text_after_command = message.text.split("/post", 1)[1].strip()

        if "|" not in raw_text_after_command:
            return message.reply("⚠️ Use format: /post Title | Content")

        # split("|", 1) মানে শুধুমাত্র প্রথম "|" দিয়ে ভাগ করা হবে
        title, body = [x.strip() for x in raw_text_after_command.split("|", 1)]
        
        # নিশ্চিত করুন যে টাইটেল বা বডি খালি নয়
        if not title or not body:
            return message.reply("⚠️ Title and Content cannot be empty. Use format: /post Title | Content")

        html_content = format_html(title, body)

        sent = publish_to_blogger(title, html_content)
        if sent:
            message.reply("✅ Posted to Blogger!")
        else:
            message.reply("❌ Failed to post. Check your API key and Blog ID or other issues. See logs for details.")

    except Exception as e:
        # এরর হ্যান্ডলিং আরও সুনির্দিষ্ট হতে পারে, তবে এটি বেসিক কাজের জন্য যথেষ্ট
        message.reply(f"❌ An unexpected error occurred: {e}")
        print(f"Error in post_to_blog: {e}") # সার্ভার লগ দেখার জন্য

print("🤖 Blogger Bot is running...")
app.run()

