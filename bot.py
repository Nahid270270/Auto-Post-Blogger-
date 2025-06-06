import os
import asyncio
import logging
import requests
from flask import Flask, request, jsonify, abort
from pyrogram import Client, filters
from pyrogram.raw.functions.messages import SendMessage # for direct API calls if needed

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
    # Render.com provides the PORT, WEBHOOK_BASE_URL should be set in Render environment
    PORT = int(os.environ.get("PORT", 8080))
    WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL") 
    if not WEBHOOK_BASE_URL:
        logger.warning("WEBHOOK_BASE_URL environment variable is not set. Webhook might not be properly configured.")
except KeyError as e:
    logger.error(f"Missing environment variable: {e}. Please set all required variables.")
    # In a production environment, you might want to exit here.
    # For now, we'll let it proceed for a Flask-only test if Pyrogram fails.
    exit(1)

# --- Pyrogram Client (will be started and stopped by the main async loop) ---
# We configure Pyrogram in webhook mode here, so it listens for updates.
# However, given Flask is running, a custom webhook handling is needed.
# For this setup, we'll make Pyrogram client available but handle messages through Flask.
app = Client(
    "blogger_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
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
    Receives Telegram updates via webhook and processes them.
    This function is now async to allow await calls within it.
    """
    if not request.is_json:
        logger.error("Received non-JSON request to webhook.")
        abort(400, description="Request must be JSON")

    update = request.get_json()
    logger.info(f"Received Telegram update: {update}")

    # Process the update in a non-blocking way
    # We will simulate a Pyrogram message for our handler
    if 'message' in update and 'text' in update['message']:
        message_text = update['message']['text']
        chat_id = update['message']['chat']['id']
        
        # Create a mock message object that behaves like Pyrogram's message
        class MockMessage:
            def __init__(self, text, chat_id, bot_token):
                self.text = text
                self.chat = type('obj', (object,), {'id': chat_id})
                self.bot_token = bot_token
            
            async def reply(self, text_to_reply):
                """Sends a reply back to the Telegram chat via API."""
                send_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                payload = {
                    "chat_id": self.chat.id,
                    "text": text_to_reply,
                }
                try:
                    resp = requests.post(send_url, json=payload)
                    resp.raise_for_status()
                    logger.info(f"Reply sent to chat {self.chat.id}: {text_to_reply}")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to send reply to Telegram: {e}")

        mock_message = MockMessage(message_text, chat_id, BOT_TOKEN)
        
        # We need to manually call the 'post_to_blog' logic
        # Run the sync function in a thread to avoid blocking the async webhook
        await asyncio.to_thread(post_to_blog, app, mock_message)
    
    return jsonify({"status": "ok"}), 200

# --- Pyrogram Message Handler (Modified to be callable from webhook logic) ---
# This function's logic is now called directly from the webhook receiver.
# The @app.on_message decorator itself won't directly fire in this webhook setup,
# but the function it points to is reusable.
def post_to_blog(client, message): # No longer async, as it's run in a thread
    try:
        # Check if the command is "/post" and if it's a private chat (simulated)
        if not message.text.startswith("/post"):
            # This case should ideally be filtered before calling this function
            # For robustness, we check here.
            # In a real Pyrogram webhook, filters would handle this.
            return 
        
        # Simulate filters.private by checking chat type if needed, but MockMessage doesn't have it.
        # This function will only be called for "/post" commands now.

        raw_text_after_command = message.text.split("/post", 1)[1].strip()

        if "|" not in raw_text_after_command:
            asyncio.run(message.reply("⚠️ Use format: `/post Title | Content`")) # Using asyncio.run in a thread is fine
            return

        title, body = [x.strip() for x in raw_text_after_command.split("|", 1)]
        
        if not title or not body:
            asyncio.run(message.reply("⚠️ Title and Content cannot be empty. Use format: `/post Title | Content`"))
            return

        html_content = format_html(title, body)

        sent = publish_to_blogger(title, html_content) # This is sync
        if sent:
            asyncio.run(message.reply("✅ Posted to Blogger!"))
        else:
            asyncio.run(message.reply("❌ Failed to post. Check your API key and Blog ID or other issues. See logs for details."))

    except Exception as e:
        asyncio.run(message.reply(f"❌ An unexpected error occurred: {e}"))
        logger.error(f"Error in post_to_blog: {e}")

# --- Main Application Runner ---
async def main_async():
    logger.info("Starting Pyrogram client (for potential background use, though updates are via Flask webhook)...")
    await app.start() # Start Pyrogram client

    # --- Set Webhook URL on Telegram ---
    if WEBHOOK_BASE_URL:
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
            logger.error(f"Failed to set webhook: {e}")
    else:
        logger.warning("WEBHOOK_BASE_URL not set. Please set the webhook manually via Telegram BotFather or API if needed.")
    
    logger.info(f"Starting Flask web server on port {PORT}...")
    
    # Run Flask in a separate thread to allow main_async to continue and manage Pyrogram
    # However, running Flask with web_app.run() in a thread is tricky.
    # A more robust solution would be to use a WSGI server like Gunicorn or Hypercorn
    # to run the Flask app, and manage Pyrogram's client separately.
    # For a simple Render.com setup, the 'entrypoint' usually handles Flask,
    # and Pyrogram needs to run in the background.

    # Option 1: Run Flask with a proper WSGI server (e.g., Gunicorn) - RECOMMENDED FOR PRODUCTION
    # This example focuses on making your code runnable. For Render, your `start` command
    # might be something like `gunicorn your_module_name:web_app --workers 1 --bind 0.0.0.0:$PORT`
    # In that case, Pyrogram app.start() would need to be handled carefully alongside.

    # Option 2: Use asyncio.create_task for a non-blocking Flask run within the same loop
    # This requires a server like `hypercorn` for async Flask.
    # For `web_app.run()` (sync Flask), it's blocking.

    # Given your current Flask setup (web_app.run is blocking)
    # The best approach for Render is usually to let Render run Flask (Gunicorn)
    # and have a separate async process if Pyrogram needs to run long-polling.
    # But for webhook, Flask is the primary receiver.

    # Let's simplify for now: Pyrogram client starts, webhook is set, Flask handles requests.
    # The `app.start()` is mostly to initialize the Pyrogram client object.
    # The actual message processing is handled by the Flask webhook.
    
    # We will run Flask as a blocking process from this main entry point.
    # This means `await app.stop()` will never be reached unless Flask itself stops.
    # For Render, this is typically how it works: the web server is the main process.
    
    # To run both Flask (blocking) and keep the async loop alive for Pyrogram
    # a more advanced setup like `hypercorn` for async Flask is needed or
    # running Flask in a separate thread/process which is complicated for simple webhooks.
    
    # For the provided code structure, Flask must run as the main process.
    # Pyrogram client will be initialized, but its @on_message decorators won't directly fire
    # unless Pyrogram is running in a proper webhook mode, which it isn't here (Flask is the webhook).
    
    # So, we just ensure `app` is started and ready if needed for other Pyrogram functions.
    # The main loop will now be handled by Flask.

    # Run the Flask app, which will block.
    # It's important that this is the last blocking call in the main async function.
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.to_thread(web_app.run, host="0.0.0.0", port=PORT, debug=False))
    
    # Keep the async loop running indefinitely, so Pyrogram app can also remain 'started'.
    # This is a bit of a hacky way to keep the main async loop running while Flask blocks a thread.
    # A more robust solution would use a fully async web framework (like FastAPI or Aiohttp)
    # with Pyrogram's built-in webhook functionality.
    
    # Pyrogram client can be stopped when the application exits.
    # But as Flask is blocking, it won't reach app.stop() gracefully here.
    # For deployment, Render handles stopping the process.
    
    # This line ensures the event loop doesn't close immediately after Flask starts.
    # It's a common pattern for hybrid async/sync apps.
    while True:
        await asyncio.sleep(3600) # Sleep for a long time to keep the loop alive

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
        # Clean up Pyrogram client gracefully on exit
        if app.is_connected:
            asyncio.run(app.stop())

