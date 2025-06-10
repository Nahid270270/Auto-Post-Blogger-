import os
import logging
import threading
import asyncio
from typing import Optional

import requests
from pyrogram import Client, filters
from flask import Flask

# --------------------------
# Logging Setup
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --------------------------
# Environment Variables
# --------------------------
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
PORT = int(os.getenv("PORT", 5000))

if not all([API_ID, API_HASH, BOT_TOKEN, OMDB_API_KEY]):
    logging.error("One or more environment variables missing: API_ID, API_HASH, BOT_TOKEN, OMDB_API_KEY")
    exit(1)

# --------------------------
# Pyrogram Client Init
# --------------------------
try:
    app = Client(
        "movie_poster_bot",
        api_id=int(API_ID),
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir="."
    )
    logging.info("Pyrogram client initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Pyrogram client: {e}")
    exit(1)

# --------------------------
# Flask App Init
# --------------------------
web_app = Flask(__name__)

# --------------------------
# Utility Functions
# --------------------------

def fetch_movie_data(title: str) -> Optional[dict]:
    """
    Synchronously fetch movie data from OMDb API.
    """
    url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "False":
            logging.warning(f"Movie '{title}' not found on OMDb: {data.get('Error')}")
            return None

        logging.info(f"Fetched data for movie: {data.get('Title')}")
        return {
            "title": data.get("Title"),
            "year": data.get("Year"),
            "language": data.get("Language"),
            "poster": data.get("Poster")
        }
    except requests.Timeout:
        logging.error(f"Timeout while fetching data for '{title}'.")
    except requests.RequestException as e:
        logging.error(f"Request error for '{title}': {e}")
    except ValueError as e:
        logging.error(f"JSON decode error for '{title}': {e}")
    return None

def generate_html(data: dict, link1: str, link2: Optional[str] = None) -> str:
    """
    Generate a styled HTML snippet for the movie poster and download links.
    """
    html = f"""
<div style="max-width:720px; margin:auto; background:#121212; border-radius:12px; padding:15px; font-family: Arial, sans-serif; color:#fff; box-shadow: 0 0 15px #ff0000;">
  <div style="text-align:center; margin-bottom:15px;">
    <img src="{data['poster']}" alt="{data['title']}" style="width:100%; max-width:600px; border-radius:10px; box-shadow: 0 0 15px #ff0000;">
  </div>
  <h1 style="font-size:32px; font-weight:bold; color:#ff0000; margin:0 0 10px;">{data['title']} ({data['year']}) [{data['language']}]</h1>
  <div style="display:flex; gap:15px; justify-content:center; flex-wrap: wrap;">
    <a href="{link1}" target="_blank" style="background:#ff0000; padding:12px 30px; border-radius:7px; color:#fff; font-weight:bold; text-decoration:none; box-shadow: 0 0 8px #ff0000;">Download 1</a>
"""
    if link2:
        html += f'<a href="{link2}" target="_blank" style="background:#ff0000; padding:12px 30px; border-radius:7px; color:#fff; font-weight:bold; text-decoration:none; box-shadow: 0 0 8px #ff0000;">Download 2</a>\n'
    html += "</div></div>"
    return html

# --------------------------
# Pyrogram Handlers
# --------------------------

@app.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    logging.info(f"/start command received from user {message.from_user.id}")
    text = (
        "👋 **নমস্কার!** আমাকে একটি সিনেমার নাম এবং ডাউনলোডের লিঙ্ক পাঠান:\n\n"
        "`সিনেমার নাম | লিঙ্ক 1 | লিঙ্ক 2 (ঐচ্ছিক)`\n\n"
        "**উদাহরণ:**\n"
        "`Pathaan 2023 | https://example.com/pathaan1 | https://example.com/pathaan2`"
    )
    await message.reply(text, parse_mode="markdown")

@app.on_message(filters.private & ~filters.command("start"))
async def poster_handler(client, message):
    logging.info(f"Message from {message.from_user.id}: {message.text}")

    parts = [p.strip() for p in message.text.split("|")]
    if len(parts) < 2:
        await message.reply(
            "❗ **ভুল ফরম্যাট!** অনুগ্রহ করে এই ফরম্যাটে পাঠান:\n"
            "`সিনেমার নাম | লিঙ্ক 1 | লিঙ্ক 2 (ঐচ্ছিক)`",
            parse_mode="markdown"
        )
        logging.warning(f"Invalid format from user {message.from_user.id}: {message.text}")
        return

    title, link1 = parts[0], parts[1]
    link2 = parts[2] if len(parts) >= 3 else None

    # ডেটা sync ফাংশন থেকে নিচ্ছি কারণ pyrogram handler async কিন্তু requests sync
    movie_data = await asyncio.to_thread(fetch_movie_data, title)
    if not movie_data:
        await message.reply("❌ **সিনেমাটি খুঁজে পাওয়া যায়নি!** অনুগ্রহ করে সঠিক নাম লিখুন।")
        logging.warning(f"Movie not found for '{title}', user {message.from_user.id}")
        return

    html_code = generate_html(movie_data, link1, link2)

    await message.reply(
        "✅ **আপনার ব্লগার HTML কোড এখানে:**\n\n"
        "`এটি কপি করে আপনার ব্লগারে HTML মোডে পেস্ট করুন।`",
        parse_mode="markdown",
        quote=True
    )
    await message.reply(f"```html\n{html_code}\n```", parse_mode="markdown")

    logging.info(f"Sent HTML code for movie '{title}' to user {message.from_user.id}")

# --------------------------
# Flask Routes
# --------------------------

@web_app.route('/')
def index():
    logging.info("Flask root accessed.")
    return "Movie Poster Bot is running!"

# --------------------------
# Bot Runner Function (thread-safe with new event loop)
# --------------------------

def start_bot_thread():
    logging.info("Starting bot thread...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(app.start())
        loop.run_forever()
    except Exception as e:
        logging.error(f"Exception in bot thread: {e}")
    finally:
        loop.run_until_complete(app.stop())
        loop.close()
        logging.info("Bot thread stopped.")

# --------------------------
# Main Entry Point
# --------------------------

if __name__ == "__main__":
    logging.info("Application starting...")

    # Start bot in daemon thread so Flask can run in main thread
    bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
    bot_thread.start()

    logging.info("Bot thread started. Starting Flask web server...")
    web_app.run(host="0.0.0.0", port=PORT)
