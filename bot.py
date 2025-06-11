from flask import Flask, render_template_string, request, redirect
from pymongo import MongoClient
import requests, os
from jinja2 import Template

app = Flask(__name__)

# ✅ আপনার Render Dashboard-এর Environment Variable থেকে নিচের দুইটি সেট করবেন:
MONGO_URI = os.getenv("MONGO_URI")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

client = MongoClient(MONGO_URI)
db = client["movie_db"]
movies = db["movies"]

# ✅ Dooplay-style Homepage
index_html = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dooplay Style Movie Site</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: #121212;
      font-family: 'Segoe UI', sans-serif;
      color: #fff;
    }
    header {
      background: #1f1f1f;
      padding: 20px;
      text-align: center;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      color: #00e676;
    }
    form {
      margin-top: 10px;
    }
    input[name="q"] {
      padding: 10px;
      width: 60%;
      max-width: 350px;
      border-radius: 5px;
      border: none;
      font-size: 16px;
    }
    button {
      padding: 10px 15px;
      background: #00e676;
      border: none;
      border-radius: 5px;
      font-weight: bold;
      cursor: pointer;
    }
    .movie-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 20px;
      padding: 20px;
    }
    .movie-card {
      background: #1f1f1f;
      border-radius: 10px;
      overflow: hidden;
      transition: transform 0.2s ease;
    }
    .movie-card:hover {
      transform: scale(1.03);
    }
    .movie-card img {
      width: 100%;
      display: block;
    }
    .movie-info {
      padding: 10px;
      text-align: center;
    }
    .movie-info h3 {
      margin: 10px 0 5px;
      font-size: 16px;
      color: #fff;
    }
    .movie-info p {
      font-size: 12px;
      color: #ccc;
    }
    .watch-btn {
      display: inline-block;
      margin-top: 10px;
      background: #00e676;
      color: #000;
      padding: 6px 12px;
      text-decoration: none;
      border-radius: 5px;
      font-weight: bold;
    }
    @media (max-width: 600px) {
      input[name="q"] { width: 90%; }
      h1 { font-size: 22px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>🎬 CineFlix</h1>
    <form>
      <input type="text" name="q" placeholder="Search movies...">
      <button type="submit">Search</button>
    </form>
  </header>
  <div class="movie-grid">
    {% for m in movies %}
      <div class="movie-card">
        <img src="{{ m.poster }}" alt="{{ m.title }}">
        <div class="movie-info">
          <h3>{{ m.title }} ({{ m.year }})</h3>
          <p>{{ m.overview[:100] }}...</p>
          {% if m.link %}
            <a class="watch-btn" href="{{ m.link }}" target="_blank">▶ Watch</a>
          {% endif %}
        </div>
      </div>
    {% endfor %}
  </div>
</body>
</html>
""")

# ✅ Simple Admin Panel (add movie)
admin_html = Template("""
<!DOCTYPE html>
<html>
<head>
  <title>Add Movie</title>
  <style>
    body { background: #111; color: #fff; text-align: center; font-family: sans-serif; }
    form { margin-top: 50px; }
    input { padding: 10px; margin: 10px; width: 250px; }
    button { padding: 10px 20px; background: #00e676; border: none; color: #000; font-weight: bold; border-radius: 5px; }
  </style>
</head>
<body>
  <h2>🎬 Add Movie to CineFlix</h2>
  <form method="post">
    <input name="title" placeholder="Movie Title"><br>
    <input name="link" placeholder="Watch/Download Link"><br>
    <button type="submit">Add Movie</button>
  </form>
</body>
</html>
""")

# ✅ Home Page (search or show latest)
@app.route('/')
def home():
    query = request.args.get('q')
    if query:
        result = movies.find({"title": {"$regex": query, "$options": "i"}})
    else:
        result = movies.find().sort('_id', -1).limit(24)
    return index_html.render(movies=result)

# ✅ Admin Panel: Add Movie using TMDB
@app.route('/admin', methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        title = request.form.get("title")
        link = request.form.get("link")
        tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
        res = requests.get(tmdb_url).json()
        if res["results"]:
            data = res["results"][0]
            movie = {
                "title": data["title"],
                "overview": data.get("overview", ""),
                "poster": f"https://image.tmdb.org/t/p/w500{data['poster_path']}" if data.get("poster_path") else "",
                "year": data.get("release_date", "")[:4],
                "link": link or ""
            }
            movies.insert_one(movie)
            return redirect('/admin')
    return admin_html.render()

# ✅ Start server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
