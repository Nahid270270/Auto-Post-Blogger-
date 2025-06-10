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
# প্রোডাকশনে সরাসরি কোডে না লিখে এভাবে লোড করা নিরাপদ
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OMDB_API_KEY = os.environ.get("OMDB_API_KEY")
PORT = int(os.environ.get("PORT", 5000)) # Render এর জন্য পোর্ট

# নিশ্চিত করুন যে প্রয়োজনীয় এনভায়রনমেন্ট ভেরিয়েবলগুলো সেট করা আছে
if not all([API_ID, API_HASH, BOT_TOKEN, OMDB_API_KEY]):
    logging.error("ERROR: One or more environment variables (API_ID, API_HASH, BOT_TOKEN, OMDB_API_KEY) are not set. Exiting.")
    exit(1) # ভেরিয়েবল না থাকলে প্রোগ্রাম বন্ধ করুন

# --- Pyrogram ক্লায়েন্ট ইনিশিয়ালাইজেশন ---
try:
    app = Client(
        "movie_poster_bot",
        api_id=int(API_ID), # API_ID স্ট্রিং হিসাবে আসে, তাই int এ রূপান্তর করুন
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir="." # সেশন ফাইল তৈরি করার জন্য একটি ফোল্ডার নির্দিষ্ট করুন
    )
    logging.info("Pyrogram client initialized successfully.")
except Exception as e:
    logging.error(f"FATAL: Error initializing Pyrogram client: {e}")
    exit(1)

# --- Flask অ্যাপ্লিকেশন তৈরি ---
web_app = Flask(__name__)

# --- ইউটিলিটি ফাংশন ---

async def get_movie_data(title: str) -> dict | None:
    """
    OMDb API থেকে সিনেমার ডেটা ফেচ করে।
    """
    url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url, timeout=10) # 10 সেকেন্ডের টাইমআউট যোগ করা হয়েছে
        response.raise_for_status() # HTTP ত্রুটির জন্য চেক করুন (4xx/5xx)
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
    except ValueError as e: # JSON ডিকোড করার ত্রুটি
        logging.error(f"JSON decoding error for movie data of '{title}': {e}")
        return None

def generate_html(data: dict, link1: str, link2: str | None = None) -> str:
    """
    সিনেমার ডেটা এবং ডাউনলোডের লিঙ্ক ব্যবহার করে একটি HTML কোড তৈরি করে।
    """
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
    """
    /start কমান্ডের জন্য হ্যান্ডলার।
    """
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
    """
    সিনেমার তথ্য এবং ডাউনলোড লিঙ্ক থেকে HTML কোড তৈরি করার হ্যান্ডলার।
    """
    logging.info(f"Received message from user {message.from_user.id}: {message.text}")
    parts = [p.strip() for p in message.text.split("|")] # অতিরিক্ত স্পেস সরান

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

    # OMDb থেকে সিনেমার ডেটা আনুন
    movie_data = await get_movie_data(title)
    if not movie_data:
        logging.warning(f"Movie data not found for '{title}'. Replying to user.")
        return await message.reply("❌ **সিনেমাটি খুঁজে পাওয়া যায়নি!** অনুগ্রহ করে সঠিক নাম লিখুন।")

    # HTML কোড তৈরি করুন
    html_code = generate_html(movie_data, link1, link2)
    
    # ব্যবহারকারীকে HTML কোড পাঠান
    await message.reply(
        "✅ **আপনার ব্লগার HTML কোড এখানে:**\n\n"
        "`এটি কপি করে আপনার ব্লগারে HTML মোডে পেস্ট করুন।`",
        quote=True,
        parse_mode="markdown"
    )
    # <code> ট্যাগ ব্যবহার করে কোড ব্লক হিসেবে পাঠানো হয়েছে
    await message.reply(f"```html\n{html_code}\n```", parse_mode="markdown")
    logging.info(f"HTML code sent to user {message.from_user.id} for movie: {title}")

# --- Flask সার্ভার এবং বট রানিং লজিক ---

@web_app.route('/')
def home():
    """
    Render.com এর স্বাস্থ্য পরীক্ষার জন্য প্রাথমিক রুট।
    """
    logging.info("Flask home route accessed. Bot is running.")
    return "Movie Poster Bot is running!"

def start_bot_sync():
    """
    Pyrogram বটকে একটি পৃথক থ্রেডে সিনক্রোনাসভাবে শুরু করে।
    """
    logging.info("Starting Pyrogram bot process...")
    try:
        # Pyrogram এর app.run() স্বয়ংক্রিয়ভাবে একটি ইভেন্ট লুপ তৈরি করে এবং পরিচালনা করে
        app.run()
    except Exception as e:
        logging.error(f"FATAL: Pyrogram bot encountered an error and stopped: {e}")
    finally:
        logging.info("Pyrogram bot process finished.")


if __name__ == '__main__':
    logging.info("Application starting up...")
    
    # Pyrogram বটকে একটি পৃথক থ্রেডে চালান
    # এটি নিশ্চিত করবে যে Flask সার্ভার প্রধান থ্রেডে চলতে পারে
    bot_thread = threading.Thread(target=start_bot_sync, daemon=True)
    bot_thread.start()
    logging.info("Pyrogram bot thread initiated.")

    # Flask অ্যাপ্লিকেশন চালান
    # Render.com এই Flask সার্ভারকে একটি ওয়েব সার্ভিস হিসেবে চিনবে
    logging.info(f"Starting Flask web server on port {PORT}...")
    web_app.run(host='0.0.0.0', port=PORT)
    logging.info("Flask web server stopped. Application exiting.")

