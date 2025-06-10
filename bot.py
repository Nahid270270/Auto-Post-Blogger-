from pyrogram import Client, filters
import requests
from flask import Flask, request
import os
import threading
# import asyncio # asyncio এখানে সরাসরি প্রয়োজন নেই, Pyrogram নিজেই হ্যান্ডেল করবে

API_ID = 22697010     # আপনার API_ID
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "7347631253:AAFVbAQhRkv7XHcy-u838xGy49unjqw8RKE"
OMDB_API_KEY = "58dcfd4d"

# Pyrogram ক্লায়েন্ট ইনিশিয়ালাইজ করুন
app = Client("movie_poster_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask অ্যাপ্লিকেশন তৈরি করুন
web_app = Flask(__name__)

# OMDb থেকে সিনেমার ডেটা আনার ফাংশন
def get_movie_data(title):
    url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
    res = requests.get(url).json()
    if res.get("Response") == "False":
        return None
    return {
        "title": res.get("Title"),
        "year": res.get("Year"),
        "language": res.get("Language"),
        "poster": res.get("Poster")
    }

# HTML কোড তৈরির ফাংশন
def generate_html(data, link1, link2=None):
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

# Pyrogram স্টার্ট কমান্ড হ্যান্ডলার
@app.on_message(filters.private & filters.command("start"))
async def start(client, message):
    await message.reply("👋 Send me a movie name like:\n\n`Pathaan 2023 | https://link1.com | https://link2.com (optional)`")

# Pyrogram মুভি হ্যান্ডলার
@app.on_message(filters.private & ~filters.command("start"))
async def movie_handler(client, message):
    parts = message.text.split("|")
    if len(parts) < 2:
        return await message.reply("❗ Please provide in this format:\n`Movie Name | Download Link 1 | Download Link 2 (optional)`")

    title = parts[0].strip()
    link1 = parts[1].strip()
    link2 = parts[2].strip() if len(parts) >= 3 else None

    data = get_movie_data(title)
    if not data:
        return await message.reply("❌ Movie not found!")

    html_code = generate_html(data, link1, link2)
    await message.reply("✅ Here is your Blogger HTML Code:\n\n`Copy this and paste into Blogger HTML mode.`", quote=True)
    await message.reply(f"<code>{html_code}</code>", parse_mode="html")

# Flask রুট যা বটকে সক্রিয় রাখবে এবং পোর্ট বাইন্ডিং নিশ্চিত করবে
@web_app.route('/')
def home():
    return "Bot is running and listening!"

# Pyrogram বট চালানোর জন্য একটি ফাংশন (সংশোধিত)
def run_bot():
    print("Starting Pyrogram bot...")
    app.run() # asyncio.run() বাদ দেওয়া হয়েছে, কারণ app.run() নিজেই লুপ হ্যান্ডেল করে
    print("Pyrogram bot stopped.")

if __name__ == '__main__':
    # Pyrogram বটকে একটি পৃথক থ্রেডে চালান
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Render.com থেকে PORT এনভায়রনমেন্ট ভেরিয়েবলটি পান।
    port = int(os.environ.get("PORT", 5000))
    
    print(f"Starting Flask web server on port {port}...")
    # Flask অ্যাপ্লিকেশন চালান।
    web_app.run(host='0.0.0.0', port=port)

