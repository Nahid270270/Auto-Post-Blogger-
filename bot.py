from flask import Flask, render_template, request, redirect
from pymongo import MongoClient
import requests, os
from jinja2 import Template

app = Flask(__name__)
MONGO_URI = os.getenv("MONGO_URI")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

client = MongoClient(MONGO_URI)
db = client["movie_db"]
movies = db["movies"]

index_html = Template("""
<!DOCTYPE html>
<html>
<head>
  <title>Movie Site</title>
  <style>
    body { font-family: sans-serif; background: #111; color: #eee; text-align: center; }
    .movie { display: inline-block; width: 200px; margin: 10px; background: #222; padding: 10px; border-radius: 10px; }
    img { width: 100%; border-radius: 8px; }
    a.button { display: inline-block; background: #0f0; padding: 5px 10px; color: #000; border-radius: 5px; text-decoration: none; }
  </style>
</head>
<body>
  <h1>🎬 Movie Library</h1>
  <form>
    <input name="q" placeholder="Search..." style="padding:5px; width: 200px;">
    <button type="submit">Search</button>
  </form>
  <div>
    {% for m in movies %}
      <div class="movie">
        <img src="{{ m.poster }}" alt="{{ m.title }}">
        <h3>{{ m.title }} ({{ m.year }})</h3>
        <p>{{ m.overview[:100] }}...</p>
        {% if m.link %}
          <a class="button" href="{{ m.link }}" target="_blank">▶ Watch</a>
        {% endif %}
      </div>
    {% endfor %}
  </div>
</body>
</html>
""")

admin_html = Template("""
<!DOCTYPE html>
<html>
<head><title>Admin Panel</title></head>
<body>
  <h2>🎬 Add Movie</h2>
  <form method="post">
    <input name="title" placeholder="Movie Title"><br><br>
    <input name="link" placeholder="Watch/Download Link"><br><br>
    <button type="submit">Add Movie</button>
  </form>
</body>
</html>
""")

@app.route('/')
def home():
    query = request.args.get('q')
    if query:
        result = movies.find({"title": {"$regex": query, "$options": "i"}})
    else:
        result = movies.find().sort('_id', -1).limit(20)
    return index_html.render(movies=result)

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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
