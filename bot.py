import os
import asyncio
import logging
import requests
from flask import Flask, request, jsonify, abort
from pyrogram import Client, filters
from pyrogram.types import Message

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables Loading ---
required_vars = ["API_ID", "API_HASH", "BOT_TOKEN", "BLOGGER_API_KEY", "BLOG_ID", "WEBHOOK_BASE_URL"]
missing_vars = [var for var in required_vars if var not in os.environ]

if missing_vars:
    logger.critical(f"Missing required environment variables: {missing_vars}")
    exit(1)

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
BLOGGER_API_KEY = os.environ["BLOGGER_API_KEY"]
BLOG_ID = os.environ["BLOG_ID"]
WEBHOOK_BASE_URL = os.environ["WEBHOOK_BASE_URL"]
PORT = int(os.environ.get("PORT", 8080))

# --- Pyrogram Client ---
app = Client(
    "blogger_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    no_updates=True,
    take_out=True
)

# --- Flask Web Application ---
web_app = Flask(__name__)

# --- Blogger Post Function ---
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

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Blogger API error: {e}")
        return False

# --- Telegram Webhook Receiver ---
@web_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook_receiver():
    if not request.is_json:
        return abort(400, description="Request must be JSON")

    update_data = request.get_json()
    logger.info(f"Received update: {update_data}")

    try:
        asyncio.run(app.process_update(update_data))
    except Exception as e:
        logger.error(f"Update processing failed: {e}", exc_info=True)

    return jsonify({"status": "ok"}), 200

# --- Command Handler ---
@app.on_message(filters.command("post") & filters.private)
async def post_to_blog(client, message: Message):
    try:
        raw_text = message.text.split("/post", 1)[1].strip()

        if "|" not in raw_text:
            return await message.reply("⚠️ Use format: `/post Title | Content`")

        title, body = [x.strip() for x in raw_text.split("|", 1)]
        if not title or not body:
            return await message.reply("⚠️ Title and Content cannot be empty.")

        html_content = format_html(title, body)
        success = await asyncio.to_thread(publish_to_blogger, title, html_content)

        if success:
            await message.reply("✅ Posted to Blogger!")
        else:
            await message.reply("❌ Failed to post to Blogger.")

    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        await message.reply(f"❌ Error: {e}")

# --- Main ---
async def main():
    await app.start()

    # Set webhook
    webhook_url = f"{WEBHOOK_BASE_URL}/{BOT_TOKEN}"
    try:
        current = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo").json()
        if current.get('result', {}).get('url') != webhook_url:
            resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")
            resp.raise_for_status()
            logger.info(f"Webhook set to {webhook_url}")
        else:
            logger.info("Webhook already set correctly.")
    except Exception as e:
        logger.error(f"Webhook setup failed: {e}")

    logger.info(f"Running Flask app on port {PORT}...")
    web_app.run(host="0.0.0.0", port=PORT, debug=False)

    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted. Exiting.")
    except Exception as e:
        logger.critical(f"Startup error: {e}", exc_info=True)
