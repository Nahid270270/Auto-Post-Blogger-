import os
import requests
from pyrogram import Client, filters
from flask import Flask
import asyncio
import logging
import threading

# --- লগিং সেটআপ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- এনভায়রনমেন্ট ভেরিয়েবল লোড ---
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OMDB_API_KEY = os.environ.get("OMDB_API_KEY")
PORT = int(os.environ.get("PORT", 5000))  # Render.com এর জন্য পোর্ট

if not all([API_ID, API_HASH, BOT_TOKEN, OMDB_API_KEY]):
    logging.error("ERROR: One or more environment variables (API_ID, API_HASH, BOT_TOKEN, OMDB_API_KEY) are not set. Exiting.")
    exit(1)

# --- Pyrogram ক্লায়েন্ট ইনিশিয়ালাইজেশন ---
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
    logging.error(f"FATAL: Error initializing Pyrogram client: {e}")
    exit(1)

# --- Flask অ্যাপ্লিকেশন তৈরি ---
web_app = Flask(__name__)

# --- ইউটিলিটি ফাংশন ---

async def get_movie_data(title: str) -> dict | None:
    url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        res = response.json()

        if res.get("Response") == "False":
            logging.warning(f"Movie '{title}' not found on OMDb. Error: {res.get('Error')}")
            return None

        logging.info(f"Successfully fetched data for movie: {res.get('Title')}")
        return {
            "title": res.get("Title"),
            "year": res.get("Year"),
            "language": res.get("Language"),
            "poster": res.get("Poster")
        }
    except requests.exceptions.Timeout:
        logging.error(f"Timeout occurred while fetching movie data for '{title}'.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network or request error fetching movie data for '{title}': {e}")
        return None
    except ValueError as e:
        logging.error(f"JSON decoding error for movie data of '{title}': {e}")
        return None

def generate_html(data: dict, link1: str, link2: str | None = None) -> str:
    logging.info(f"Generating HTML for movie: {data['title']}")
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

# --- Pyrogram হ্যান্ডলার ---

@app.on_message(filters.private & filters.command("start"))
async def start_command(client, message):
    logging.info(f"Received /start command from user: {message.from_user.id}")
    await message.reply(
        "👋 **নমস্কার!** আমাকে একটি সিনেমার নাম এবং ডাউনলোডের লিঙ্ক পাঠান:\n\n"
        "`সিনেমার নাম | লিঙ্ক 1 | লিঙ্ক 2 (ঐচ্ছিক)`\n\n"
        "**উদাহরণ:**\n"
        "`Pathaan 2023 | https://example.com/pathaan1 | https://example.com/pathaan2`",
        parse_mode="markdown"
    )

@app.on_message(filters.private & ~filters.command("start"))
async def movie_poster_handler(client, message):
    logging.info(f"Received message from user {message.from_user.id}: {message.text}")
    parts = [p.strip() for p in message.text.split("|")]

    if len(parts) < 2:
        logging.warning(f"Invalid format from user {message.from_user.id}: '{message.text}'")
        return await message.reply(
            "❗ **ভুল ফরম্যাট!** অনুগ্রহ করে এই ফরম্যাটে পাঠান:\n"
            "`সিনেমার নাম | লিঙ্ক 1 | লিঙ্ক 2 (ঐচ্ছিক)`",
            parse_mode="markdown"
        )

    title = parts[0]
    link1 = parts[1]
    link2 = parts[2] if len(parts) >= 3 else None

    movie_data = await get_movie_data(title)
    if not movie_data:
        logging.warning(f"Movie data not found for '{title}'. Replying to user.")
        return await message.reply("❌ **সিনেমাটি খুঁজে পাওয়া যায়নি!** অনুগ্রহ করে সঠিক নাম লিখুন।")

    html_code = generate_html(movie_data, link1, link2)

    await message.reply(
        "✅ **আপনার ব্লগার HTML কোড এখানে:**\n\n"
        "`এটি কপি করে আপনার ব্লগারে HTML মোডে পেস্ট করুন।`",
        quote=True,
        parse_mode="markdown"
    )
    await message.reply(f"```html\n{html_code}\n```", parse_mode="markdown")
    logging.info(f"HTML code sent to user {message.from_user.id} for movie: {title}")

# --- Flask রুট ---

@web_app.route('/')
def home():
    logging.info("Flask home route accessed. Bot is running.")
    return "Movie Poster Bot is running!"

# --- বট চালানোর জন্য ফাংশন ---

def start_bot_sync():
    logging.info("Bot thread started.")
    try:
        app.run()  # Pyrogram নিজেই asyncio লুপ সামলে নেয়, start এবং stop করে
    except Exception as e:
        logging.error(f"Bot encountered an error: {e}")
    logging.info("Bot thread stopped.")

if __name__ == '__main__':
    logging.info("Application starting up...")

    bot_thread = threading.Thread(target=start_bot_sync, daemon=True)
    bot_thread.start()
    logging.info("Bot thread initiated.")

    web_app.run(host='0.0.0.0', port=PORT)
