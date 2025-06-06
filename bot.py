import os
import asyncio
import logging
import requests
from flask import Flask, request, jsonify, abort
from pyrogram import Client, filters
from pyrogram.types import Message
# from flask_asyncio import AsyncFlask # REMOVED: No longer needed

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
        exit(1) 

except KeyError as e:
    logger.error(f"Missing environment variable: {e}. Please set all required variables.")
    exit(1) 

# --- Pyrogram Client ---
# IMPORTANT: For webhook mode, Pyrogram client itself doesn't need to do long-polling.
# We explicitly set `no_updates=True` and `take_out=True` to signal this.
# The updates will be fed to `app.process_update()` by the Flask webhook.
app = Client(
    "blogger_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    no_updates=True, # Tells Pyrogram not to start its own update fetching
    take_out=True    # Further optimizes for webhook (avoids redundant API calls)
)

# --- Flask Web Application ---
# Using standard Flask, as Pyrogram's `process_update` is asynchronous but can be called
# from a sync Flask route using `asyncio.run` or `asyncio.create_task` with a pre-existing loop.
# Or, if Flask route is async (using an async WSGI like Hypercorn), then `await app.process_update`.
# For simplicity with `web_app.run()`, we'll use `asyncio.run` locally in the Flask route.
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
def telegram_webhook_receiver():
    """
    Receives Telegram updates via webhook and passes them to Pyrogram.
    This route is sync, but we use asyncio.run to call async methods.
    """
    if not request.is_json:
        logger.error("Received non-JSON request to webhook.")
        abort(400, description="Request must be JSON")

    update_data = request.get_json()
    logger.info(f"Received Telegram update: {update_data}")

    try:
        # Get the current running event loop. If none, create one.
        # This is crucial for running async Pyrogram methods within a sync Flask route.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Pass the raw update data to Pyrogram for processing in the current loop
        # We use asyncio.run_coroutine_threadsafe to schedule it in the loop
        # and wait for it. Or more simply, asyncio.run if this is the only async context.
        # Given Flask typically runs on a sync WSGI server (like gunicorn),
        # asyncio.run() here is safer as it creates its own loop per request if needed.
        asyncio.run(app.process_update(update_data))
        logger.info("Update successfully passed to Pyrogram.")
    except Exception as e:
        logger.error(f"Error processing Telegram update via Pyrogram: {e}", exc_info=True)
    
    return jsonify({"status": "ok"}), 200

# --- Pyrogram Message Handler ---
@app.on_message(filters.command("post") & filters.private)
async def post_to_blog_command_handler(client, message: Message):
    """
    Handles the /post command.
    This function is async, allowing direct use of await message.reply()
    and await asyncio.to_thread().
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
        # to avoid blocking the async event loop of Pyrogram.
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
    # This `app.start()` call is important to initialize Pyrogram's internal structures
    # even in webhook mode, so `app.process_update()` can function correctly.
    await app.start() 

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
    
    logger.info(f"Starting Flask web server on port {PORT}...")
    
    # Run the Flask app. This is a blocking call.
    # When deployed on Render, `web_app.run` will be the main process.
    # Pyrogram client needs to be started before this to handle updates.
    web_app.run(host="0.0.0.0", port=PORT, debug=False)

    # These lines might not be reached if Flask server runs indefinitely
    logger.info("Flask web server stopped. Stopping Pyrogram client...")
    await app.stop() 

if __name__ == "__main__":
    # Ensure a current event loop is available for async functions
    # and run the main async task.
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application shutting down due to keyboard interrupt.")
        # Attempt to stop Pyrogram client gracefully on exit
        if app.is_connected:
            asyncio.run(app.stop())
    except Exception as e:
        logger.critical(f"An unhandled exception occurred during application startup: {e}", exc_info=True)

