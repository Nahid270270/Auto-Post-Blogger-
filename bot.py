import os
import asyncio
import logging
import requests
from flask import Flask, request, jsonify, abort
from pyrogram import Client, filters
from pyrogram.types import Message
from flask_asyncio import AsyncFlask # Import AsyncFlask

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables Loading ---
try:
    API_ID = int(os.environ["API_ID"])
    API_HASH = os.environ["API_HASH"]
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    BLOGGER_API_KEY = os.environ["BLOGGER_API_KEY"]
    BLOG_ID = os.environ["BLOG_ID"]
    
    # Render.com provides the PORT. WEBHOOK_BASE_URL must be set in Render environment.
    PORT = int(os.environ.get("PORT", 8080))
    WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL") 
    
    if not WEBHOOK_BASE_URL:
        logger.error("WEBHOOK_BASE_URL environment variable is NOT SET. Webhook will not be configured correctly. Please set it to your Render.com service's public URL.")
        # Exit if critical env var is missing, as webhook won't work
        exit(1) 

except KeyError as e:
    logger.error(f"Missing environment variable: {e}. Please set all required variables.")
    exit(1) # Exit if essential env vars are missing

# --- Pyrogram Client ---
app = Client(
    "blogger_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    # In webhook mode, Pyrogram does not need to start long-polling.
    # It will process updates via the webhook endpoint.
    # We'll use a specific setup for Flask to feed updates to Pyrogram.
)

# --- Flask Web Application ---
# Use AsyncFlask to properly handle async operations within Flask
web_app = AsyncFlask(__name__)

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
        logger.info(f"Blogger API Request URL: {url}")
        logger.info(f"Blogger API Request Data: {data}")
        logger.info(f"Blogger API Response Status: {response.status_code}")
        logger.info(f"Blogger API Response Body: {response.text}")
        
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Network or request error during Blogger API call: {e}")
        return False

# --- Telegram Webhook Receiver Endpoint ---
@web_app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def telegram_webhook_receiver():
    """
    Receives Telegram updates via webhook and passes them to Pyrogram.
    """
    if not request.is_json:
        logger.error("Received non-JSON request to webhook.")
        abort(400, description="Request must be JSON")

    update_data = request.get_json()
    logger.info(f"Received Telegram update: {update_data}")

    try:
        # Pass the raw update data to Pyrogram for processing
        # This allows Pyrogram to handle all its decorators like @app.on_message
        await app.process_update(update_data)
        logger.info("Update successfully passed to Pyrogram.")
    except Exception as e:
        logger.error(f"Error processing Telegram update via Pyrogram: {e}")
    
    return jsonify({"status": "ok"}), 200

# --- Pyrogram Message Handler ---
@app.on_message(filters.command("post") & filters.private)
async def post_to_blog_command_handler(client, message: Message):
    """
    Handles the /post command.
    This function is now async, allowing direct use of await message.reply().
    """
    logger.info(f"Received /post command from chat ID: {message.chat.id}")
    try:
        raw_text_after_command = message.text.split("/post", 1)[1].strip()

        if "|" not in raw_text_after_command:
            await message.reply("⚠️ Use format: `/post Title | Content`")
            logger.warning(f"Invalid /post format from {message.chat.id}: No '|' found.")
            return

        title, body = [x.strip() for x in raw_text_after_command.split("|", 1)]
        
        if not title or not body:
            await message.reply("⚠️ Title and Content cannot be empty. Use format: `/post Title | Content`")
            logger.warning(f"Invalid /post format from {message.chat.id}: Empty title or body.")
            return

        html_content = format_html(title, body)

        # Call the sync function publish_to_blogger in a separate thread
        # to avoid blocking the async event loop.
        sent = await asyncio.to_thread(publish_to_blogger, title, html_content) 
        
        if sent:
            await message.reply("✅ Posted to Blogger!")
            logger.info(f"Successfully posted to Blogger for chat ID: {message.chat.id}")
        else:
            await message.reply("❌ Failed to post. Check your API key and Blog ID or other issues. See logs for details.")
            logger.error(f"Failed to post to Blogger for chat ID: {message.chat.id}")

    except Exception as e:
        await message.reply(f"❌ An unexpected error occurred: {e}")
        logger.error(f"Error in post_to_blog_command_handler for chat ID {message.chat.id}: {e}", exc_info=True)

# --- Main Application Runner ---
async def main():
    logger.info("Starting Pyrogram client...")
    await app.start() # Start Pyrogram client

    # --- Set Webhook URL on Telegram ---
    webhook_url = f"{WEBHOOK_BASE_URL}/{BOT_TOKEN}"
    try:
        # Check current webhook to avoid unnecessary updates
        get_webhook_info_resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo")
        get_webhook_info_resp.raise_for_status()
        current_webhook_info = get_webhook_info_resp.json()

        if current_webhook_info.get('result', {}).get('url') == webhook_url:
            logger.info(f"Webhook already set to: {webhook_url}")
        else:
            response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")
            response.raise_for_status()
            logger.info(f"Webhook set to: {webhook_url}, Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to set webhook: {e}. Please ensure WEBHOOK_BASE_URL is correct and accessible.")
        # Do not exit, but log the error. The bot might still receive updates if webhook was set manually.
    
    logger.info(f"Starting Flask web server on port {PORT}...")
    
    # Run the Flask app within the same asyncio event loop
    # This will block the current coroutine until Flask server stops
    await web_app.run(host="0.0.0.0", port=PORT, debug=False)

    # These lines might not be reached if Flask server runs indefinitely
    logger.info("Flask web server stopped. Stopping Pyrogram client...")
    await app.stop() # Pyrogram client stops when Flask app stops

if __name__ == "__main__":
    # This ensures a clean run and handles potential RuntimeError if loop already exists.
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application shutting down due to keyboard interrupt.")
        # app.stop() will be called if the main() loop reaches its end,
        # or if the async tasks are properly cancelled.
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)

