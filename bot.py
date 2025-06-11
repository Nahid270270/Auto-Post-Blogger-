from flask import Flask, render_template_string, request, redirect
from pymongo import MongoClient
import requests, os

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

client = MongoClient(MONGO_URI)
db = client["movie_db"]
movies = db["movies"]

index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Movie Dokan Style</title>
<style>
  /* Reset & basics */
  * {
    box-sizing: border-box;
  }
  body {
    margin: 0; background: #121212; color: #eee;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }
  a { text-decoration: none; color: inherit; }
  a:hover { color: #1db954; }
  
  header {
    position: sticky;
    top: 0; left: 0; right: 0;
    background: #181818;
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 100;
    box-shadow: 0 2px 5px rgba(0,0,0,0.7);
  }
  header h1 {
    margin: 0;
    font-weight: 700;
    font-size: 24px;
    color: #1db954;
  }
  form {
    flex-grow: 1;
    margin-left: 20px;
  }
  input[type="search"] {
    width: 100%;
    max-width: 400px;
    padding: 8px 12px;
    border-radius: 30px;
    border: none;
    font-size: 16px;
    outline: none;
  }

  main {
    max-width: 1200px;
    margin: 20px auto;
    padding: 0 15px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill,minmax(180px,1fr));
    gap: 20px;
  }
  .movie-card {
    background: #181818;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 0 8px rgba(0,0,0,0.6);
    transition: transform 0.2s ease;
    position: relative;
  }
  .movie-card:hover {
    transform: scale(1.05);
    box-shadow: 0 0 15px #1db954;
  }
  .movie-poster {
    width: 100%;
    display: block;
  }
  .movie-info {
    padding: 10px;
  }
  .movie-title {
    font-size: 18px;
    font-weight: 700;
    margin: 0 0 4px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .movie-year {
    font-size: 14px;
    color: #aaa;
    margin-bottom: 6px;
  }
  .badge {
    position: absolute;
    top: 8px;
    left: 8px;
    background: #1db954;
    color: #000;
    font-weight: 700;
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    user-select: none;
  }
  .overview {
    font-size: 13px;
    color: #ccc;
    max-height: 0;
    opacity: 0;
    padding: 0 10px;
    overflow: hidden;
    transition: max-height 0.3s ease, opacity 0.3s ease;
  }
  .movie-card:hover .overview {
    max-height: 80px;
    opacity: 1;
    margin-bottom: 10px;
  }
  .watch-btn {
    display: block;
    background: #1db954;
    color: #000;
    font-weight: 700;
    padding: 8px 0;
    border-radius: 0 0 8px 8px;
    text-align: center;
    font-size: 16px;
    user-select: none;
  }
  .watch-btn:hover {
    background: #17a34a;
  }

  /* Mobile adjustments */
  @media (max-width: 600px) {
    .movie-title {
      font-size: 16px;
    }
    .watch-btn {
      font-size: 14px;
      padding: 6px 0;
    }
  }
</style>
</head>
<body>
<header>
  <h1>Movie Dokan</h1>
  <form method="GET" action="/">
    <input type="search" name="q" placeholder="Search movies..." value="{{ query|default('') }}" />
  </form>
</header>
<main>
  {% if movies|length == 0 %}
    <p style="text-align:center; color:#999; margin-top: 40px;">No movies found.</p>
  {% else %}
  <div class="grid">
    {% for m in movies %}
    <div class="movie-card">
      {% if m.poster %}
        <img class="movie-poster" src="{{ m.poster }}" alt="{{ m.title }}">
      {% else %}
        <div style="height:270px; background:#333; display:flex;align-items:center;justify-content:center;color:#777;">
          No Image
        </div>
      {% endif %}
      {% if m.quality %}
        <div class="badge">{{ m.quality }}</div>
      {% endif %}
      <div class="movie-info">
        <h3 class="movie-title" title="{{ m.title }}">{{ m.title }}</h3>
        <div class="movie-year">{{ m.year }}</div>
        <p class="overview">{{ m.overview }}</p>
      </div>
      {% if m.link %}
        <a class="watch-btn" href="{{ m.link }}" target="_blank" rel="noopener">▶ Watch</a>
      {% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}
</main>
</body>
</html>
"""

admin_html = """
<!DOCTYPE html>
<html>
<head>
  <title>Admin Panel - Movie Dokan</title>
  <style>
    body { font-family: Arial, sans-serif; background: #121212; color: #eee; padding: 20px; }
    h2 { color: #1db954; }
    form { max-width: 400px; margin-top: 20px; }
    input, button {
      width: 100%;
      padding: 10px;
      margin-bottom: 15px;
      border-radius: 5px;
      border: none;
      font-size: 16px;
    }
    input {
      background: #222;
      color: #eee;
    }
    button {
      background: #1db954;
      color: #000;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.3s ease;
    }
    button:hover {
      background: #17a34a;
    }
  </style>
</head>
<body>
  <h2>Add Movie</h2>
  <form method="post">
    <input name="title" placeholder="Movie Title" required />
    <input name="link" placeholder="Watch/Download Link" />
    <input name="quality" placeholder="Quality tag (e.g. HD, Hindi Dubbed)" />
    <button type="submit">Add Movie</button>
  </form>
</body>
</html>
"""

@app.route('/')
def home():
    query = request.args.get('q')
    if query:
        result = movies.find({"title": {"$regex": query, "$options": "i"}})
    else:
        result = movies.find().sort('_id', -1).limit(30)
    return render_template_string(index_html, movies=result, query=query)

@app.route('/admin', methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        title = request.form.get("title")
        link = request.form.get("link")
        quality = request.form.get("quality") or ""
        tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
        res = requests.get(tmdb_url).json()
        if res["results"]:
            data = res["results"][0]
            movie = {
                "title": data["title"],
                "overview": data.get("overview", ""),
                "poster": f"https://image.tmdb.org/t/p/w500{data['poster_path']}" if data.get("poster_path") else "",
                "year": data.get("release_date", "")[:4],
                "link": link or "",
                "quality": quality.upper()
            }
            movies.insert_one(movie)
            return redirect('/admin')
    return render_template_string(admin_html)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
