from pyrogram import Client, filters
import requests
import os
from flask import Flask, request, abort, jsonify # Flask লাইব্রেরি
import asyncio # Asynchronous operations এর জন্য
import logging # লগিং এর জন্য

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 🔐 Load sensitive data from environment variables (server-based)
try:
    API_ID = int(os.environ["API_ID"])
    API_HASH = os.environ["API_HASH"]
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    BLOGGER_API_KEY = os.environ["BLOGGER_API_KEY"]
    BLOG_ID = os.environ["BLOG_ID"]
    # Render.com স্বয়ংক্রিয়ভাবে PORT এনভায়রনমেন্ট ভেরিয়েবল সরবরাহ করে
    PORT = int(os.environ.get("PORT", 8080)) # যদি PORT না থাকে, ডিফল্ট 8080
except KeyError as e:
    logger.error(f"Missing environment variable: {e}. Please set all required variables.")
    exit(1)

# Pyrogram Client
app = Client(
    "blogger_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Flask Web Application
web_app = Flask(__name__)

# --- ব্লগার পোস্ট করার ফাংশন (আগের মতোই) ---
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
        
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logger.error(f"Network or request error during Blogger API call: {e}")
        return False

# --- টেলিগ্রাম মেসেজ হ্যান্ডলার (Pyrogram এর জন্য) ---
# Pyrogram আপডেট প্রসেস করার জন্য একটি async ফাংশন
async def process_telegram_update(update_json):
    """Processes a raw Telegram update JSON."""
    try:
        # Pyrogram এর নিজস্ব Update অবজেক্ট তৈরি করে প্রসেস করা
        # এটি ম্যানুয়ালি করা কিছুটা জটিল, তবে Pyrogram এর internal methods ব্যবহার করা যায়।
        # আরও সহজ হলো Pyrogram এর নিজস্ব webhook handler ব্যবহার করা যদি থাকে।
        # কিন্তু সরাসরি request.json থেকে update লোড করাটা Pyrogram এর জন্য স্ট্যান্ডার্ড নয়।
        # এর পরিবর্তে, Pyrogram এর AsyncMethods.process_update() ব্যবহার করা যেতে পারে।

        # The following is a simplified approach, a more robust solution would involve
        # creating a Pyrogram Update object from the JSON.
        # For a Flask integration, it's often easier to just pass the raw update to Pyrogram's handlers
        # or use a library that bridges Flask and Pyrogram's async capabilities.
        
        # For simplicity and to reuse your existing @app.on_message decorators:
        # We need to manually call the handlers.
        # This part requires more advanced Pyrogram knowledge for a truly robust webhook setup.
        # A direct way often involves running Pyrogram's client in webhook mode,
        # which isn't directly compatible with Flask's app.run() without some bridging.

        # Let's simplify the processing for the example:
        # We'll just assume a basic text message for now to fit the /post command.
        # In a real webhook, you'd parse the 'update_json' to extract the message
        # and then simulate a Pyrogram 'Message' object or call your 'post_to_blog' logic directly.

        # For this example, we will directly call the logic from the webhook:
        if 'message' in update_json and 'text' in update_json['message']:
            message_text = update_json['message']['text']
            chat_id = update_json['message']['chat']['id']

            # Simulate Pyrogram Message object for simpler integration
            class MockMessage:
                def __init__(self, text, chat_id):
                    self.text = text
                    self.chat = type('obj', (object,), {'id': chat_id}) # Mock chat object
                
                async def reply(self, text_to_reply):
                    # For a webhook, we can't use message.reply directly.
                    # We need to send a request back to Telegram API.
                    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    payload = {
                        "chat_id": self.chat.id,
                        "text": text_to_reply,
                    }
                    try:
                        resp = requests.post(send_url, json=payload)
                        resp.raise_for_status() # Raise an exception for bad status codes
                        logger.info(f"Reply sent to chat {self.chat.id}: {text_to_reply}")
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Failed to send reply to Telegram: {e}")

            mock_message = MockMessage(message_text, chat_id)
            
            # Now call your existing post_to_blog logic
            # Note: post_to_blog is NOT async, so it needs to be run in a thread or directly called
            # For simplicity, calling directly, but in a real async app, use run_in_executor
            post_to_blog(app, mock_message) # Pass 'app' as client, and mock_message

    except Exception as e:
        logger.error(f"Error processing Telegram update: {e}")

# --- Flask ওয়েবহুক এন্ডপয়েন্ট ---
@web_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook_receiver():
    # Telegram sends updates to this URL as POST requests
    if not request.is_json:
        abort(400) # Bad Request if not JSON

    update = request.get_json()
    logger.info(f"Received Telegram update: {update}")

    # Process the update in a non-blocking way (for Flask)
    # Using asyncio.create_task to run the async Pyrogram processing in the background
    asyncio.create_task(process_telegram_update(update))
    
    return jsonify({"status": "ok"}), 200 # Always return 200 OK to Telegram quickly

# --- আপনার Pyrogram মেসেজ হ্যান্ডলার (আগের মতোই) ---
# Note: For webhook mode, these decorators might not fire directly from Flask webhook.
# We manually call the logic from process_telegram_update.
# So, this part needs careful consideration if you have many Pyrogram decorators.
# For '/post' command, we have moved the logic to process_telegram_update to be called directly.
# If you have other commands, you'd need a more robust Pyrogram webhook setup.

@app.on_message(filters.command("post") & filters.private)
def post_to_blog(client, message): # Keep this function for logic, but it's called manually now
    try:
        # For webhook, message.reply needs to be adapted or use send_message API directly
        # The MockMessage class handles this for now.

        raw_text_after_command = message.text.split("/post", 1)[1].strip()

        if "|" not in raw_text_after_command:
            # We use await message.reply if using Pyrogram's native webhook, but for Flask
            # and direct call, we need to adapt message.reply or log.
            # In MockMessage, we've implemented a sync reply.
            asyncio.run(message.reply("⚠️ Use format: /post Title | Content")) # Ensure it's awaitable
            return

        title, body = [x.strip() for x in raw_text_after_command.split("|", 1)]
        
        if not title or not body:
            asyncio.run(message.reply("⚠️ Title and Content cannot be empty. Use format: /post Title | Content"))
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

# --- বট চালানো ---
async def main():
    logger.info("Starting Pyrogram client...")
    await app.start() # Pyrogram client starts

    # Set webhook URL on Telegram (important! Replace with your Render service URL)
    # This URL should be your Render.com service URL + /BOT_TOKEN
    # Example: https://your-service-name.onrender.com/YOUR_BOT_TOKEN
    # You MUST get your Render service URL AFTER deployment.
    # For initial testing, you might need to manually set it or run this part locally.
    
    # Render provides the public URL. You'd set the webhook like this:
    # WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL") # You might set this env var
    # if not WEBHOOK_BASE_URL:
    #     logger.warning("WEBHOOK_BASE_URL environment variable not set. Webhook will not be set.")
    # else:
    #     webhook_url = f"{WEBHOOK_BASE_URL}/{BOT_TOKEN}"
    #     try:
    #         response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")
    #         response.raise_for_status()
    #         logger.info(f"Webhook set to: {webhook_url}, Response: {response.json()}")
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"Failed to set webhook: {e}")

    # Start Flask web server (non-blocking)
    logger.info(f"Starting Flask web server on port {PORT}...")
    # Use await asyncio.to_thread(web_app.run, host="0.0.0.0", port=PORT) for async Flask if needed
    # Or, for simple Flask, just run it.
    web_app.run(host="0.0.0.0", port=PORT, debug=False) # debug=True locally, False in production

    logger.info("Pyrogram client stopping...")
    await app.stop() # Pyrogram client stops when Flask app stops

if __name__ == "__main__":
    # Ensure a current event loop is available for async functions
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(main())
