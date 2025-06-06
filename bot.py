import os
import re
import requests
from pyrogram import Client, filters
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

BLOGGER_API_KEY = os.getenv("BLOGGER_API_KEY")
BLOG_ID = os.getenv("BLOG_ID")

app = Client("blogger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Movie Parser ---
def parse_movie_message(text: str) -> dict:
    title_match = re.search(r"🎬\s*(.+?)\s*(\d{4})", text)
    lang_match = re.search(r"(.*?)", text)
    desc_match = re.search(r"📝(.+?)(📥|$)", text, re.DOTALL)
    link_matches = re.findall(r"(https?://[^\s]+)", text)
    tags = re.findall(r"#(\w+)", text)

    return {
        "title": title_match.group(1).strip() if title_match else "Untitled",
        "year": title_match.group(2) if title_match else "",
        "language": lang_match.group(1).strip() if lang_match else "Unknown",
        "description": desc_match.group(1).strip() if desc_match else "No description.",
        "download_links": link_matches,
        "labels": tags,
    }

# --- HTML Template ---
def make_html_post(movie: dict) -> dict:
    # Format download links as HTML list
    link_html = "".join(
        f'<li><a href="{link}" target="_blank" rel="nofollow">Download Link {i+1}</a></li>'
        for i, link in enumerate(movie["download_links"])
    )
    html = f"""
    <h2>{movie['title']} ({movie['year']})</h2>
    <p><strong>Language:</strong> {movie['language']}</p>
    <p><strong>Description:</strong></p>
    <p>{movie['description']}</p>
    <p><strong>Download Links:</strong></p>
    <ul>{link_html}</ul>
    <hr>
    <p><em>Posted via Telegram Movie Bot</em></p>
    """

    seo_title = f"{movie['title']} ({movie['year']}) | {movie['language']} Movie Download"
    return {
        "kind": "blogger#post",
        "title": seo_title,
        "labels": movie["labels"],
        "content": html,
    }

# --- Blogger API POST ---
def post_to_blogger(post_data: dict):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    params = {"key": BLOGGER_API_KEY}
    response = requests.post(url, params=params, json=post_data)
    return response.status_code, response.json()

# --- Telegram Handler ---
@app.on_message(filters.channel & filters.text)
async def handle_channel_post(client, message):
    movie_data = parse_movie_message(message.text)
    post_data = make_html_post(movie_data)
    status, res = post_to_blogger(post_data)

    if status == 200:
        await message.reply("✅ Blogger এ পোস্ট হয়ে গেছে!")
    else:
        await message.reply(f"❌ পোস্টে সমস্যা হয়েছে!\n{res}")

if __name__ == "__main__":
    print("🤖 Bot is running...")
    app.run()
