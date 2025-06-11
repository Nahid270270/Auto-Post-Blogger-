from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId # Import ObjectId for querying by _id
import requests, os

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Check if environment variables are set
if not MONGO_URI:
    print("Error: MONGO_URI environment variable not set.")
    exit(1)
if not TMDB_API_KEY:
    print("Error: TMDB_API_KEY environment variable not set.")
    exit(1)

# Database connection
try:
    client = MongoClient(MONGO_URI)
    db = client["movie_db"]
    movies = db["movies"]
    # Optional: Create index for faster search if you use text search
    # movies.create_index([("title", "text")], default_language='english')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    exit(1)

# --- Updated index_html (Removed Watch button, made card clickable) ---
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
    -webkit-tap-highlight-color: transparent;
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
    background: linear-gradient(270deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3);
    background-size: 400% 400%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradientShift 10s ease infinite;
  }

  @keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
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
    background: #fff;
    color: #333;
  }
  input[type="search"]::placeholder {
      color: #999;
  }

  main {
    max-width: 1200px;
    margin: 20px auto;
    padding: 0 15px;
    padding-bottom: 70px;
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
    cursor: pointer; /* Indicate clickable */
  }
  .movie-card:hover {
    transform: scale(1.05);
    box-shadow: 0 0 15px #1db954;
  }
  .movie-poster {
    width: 100%;
    height: 270px;
    object-fit: cover;
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
  .badge.trending {
    background: linear-gradient(45deg, #ff0077, #ff9900);
    color: #fff;
  }

  /* Overview hidden by default in card view */
  .overview {
    display: none;
  }

  .trending-header {
      color: #fff;
      font-size: 22px;
      font-weight: 700;
      padding: 10px 15px;
      background: linear-gradient(90deg, #e44d26, #f16529);
      border-radius: 5px;
      margin-bottom: 25px;
      text-align: center;
      box-shadow: 0 2px 10px rgba(0,0,0,0.5);
  }
  .trending-header::before {
      content: '🔥';
      margin-right: 10px;
  }

  /* Mobile adjustments - START */
  @media (max-width: 768px) {
    header { padding: 8px 15px; }
    header h1 { font-size: 20px; }
    form { margin-left: 10px; }
    input[type="search"] { max-width: unset; font-size: 14px; padding: 6px 10px; }
    main { margin: 15px auto; padding: 0 10px; padding-bottom: 60px; }
    .trending-header { font-size: 18px; padding: 8px 10px; margin-bottom: 20px; }
    .grid { grid-template-columns: repeat(auto-fill,minmax(100px,1fr)); gap: 10px; }
    .movie-card { box-shadow: 0 0 5px rgba(0,0,0,0.5); }
    .movie-poster { height: 150px; }
    .movie-info { padding: 8px; }
    .movie-title { font-size: 13px; margin: 0 0 2px 0; }
    .movie-year { font-size: 11px; margin-bottom: 4px; }
    .badge { font-size: 10px; padding: 1px 4px; top: 5px; left: 5px; }
    .watch-btn { display: none; } /* Watch button now only on detail page */
  }

  @media (max-width: 480px) {
      .grid { grid-template-columns: repeat(auto-fill,minmax(90px,1fr)); }
      .movie-poster { height: 130px; }
      .movie-title { font-size: 12px; }
      .movie-year { font-size: 10px; }
  }
  /* Mobile adjustments - END */

  /* Optional: Bottom Navigation Bar styles (as seen in screenshot) */
  .bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #181818;
    display: flex;
    justify-content: space-around;
    padding: 10px 0;
    box-shadow: 0 -2px 5px rgba(0,0,0,0.7);
    z-index: 200;
  }
  .nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    color: #ccc;
    font-size: 12px;
    text-align: center;
    transition: color 0.2s ease;
  }
  .nav-item:hover {
    color: #1db954;
  }
  .nav-item i {
      font-size: 24px;
      margin-bottom: 4px;
  }
  @media (max-width: 768px) {
      .bottom-nav { padding: 8px 0; }
      .nav-item { font-size: 10px; }
      .nav-item i { font-size: 20px; margin-bottom: 2px; }
  }
</style>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
</head>
<body>
<header>
  <h1>Movie Dokan</h1>
  <form method="GET" action="/">
    <input type="search" name="q" placeholder="Search movies..." value="{{ query|default('') }}" />
  </form>
</header>
<main>
  <div class="trending-header">Trending on MovieDokan</div>
  {% if movies|length == 0 %}
    <p style="text-align:center; color:#999; margin-top: 40px;">No movies found.</p>
  {% else %}
  <div class="grid">
    {% for m in movies %}
    <a href="{{ url_for('movie_detail', movie_id=m._id) }}" class="movie-card"> {# Card is now a link #}
      {% if m.poster %}
        <img class="movie-poster" src="{{ m.poster }}" alt="{{ m.title }}">
      {% else %}
        <div style="height:270px; background:#333; display:flex;align-items:center;justify-content:center;color:#777;">
          No Image
        </div>
      {% endif %}
      {% if m.quality %}
        <div class="badge {% if m.quality == 'TRENDING' %}trending{% endif %}">{{ m.quality }}</div>
      {% endif %}
      <div class="movie-info">
        <h3 class="movie-title" title="{{ m.title }}">{{ m.title }}</h3>
        <div class="movie-year">{{ m.year }}</div>
      </div>
      {# Watch button moved to detail page #}
    </a>
    {% endfor %}
  </div>
  {% endif %}
</main>
<nav class="bottom-nav">
  <a href="{{ url_for('home') }}" class="nav-item">
    <i class="fas fa-home"></i>
    <span>Home</span>
  </a>
  <a href="#" class="nav-item">
    <i class="fas fa-film"></i>
    <span>Movie</span>
  </a>
  <a href="{{ url_for('admin') }}" class="nav-item"> {# Link to admin for quick access #}
    <i class="fas fa-plus-circle"></i>
    <span>Request</span>
  </a>
  <a href="#" class="nav-item">
    <i class="fas fa-tv"></i>
    <span>Web Series</span>
  </a>
  <a href="#" class="nav-item">
    <i class="fas fa-search"></i>
    <span>Search</span>
  </a>
</nav>
</body>
</html>
"""

# --- New detail_html template ---
detail_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{{ movie.title }} - Movie Details</title>
<style>
  /* General styles (similar to index_html for consistency) */
  * { box-sizing: border-box; }
  body { margin: 0; background: #121212; color: #eee; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
  a { text-decoration: none; color: inherit; }
  a:hover { color: #1db954; }

  header {
    position: sticky; top: 0; left: 0; right: 0;
    background: #181818; padding: 10px 20px;
    display: flex; justify-content: space-between; align-items: center; z-index: 100;
    box-shadow: 0 2px 5px rgba(0,0,0,0.7);
  }
  header h1 {
    margin: 0; font-weight: 700; font-size: 24px;
    background: linear-gradient(270deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3);
    background-size: 400% 400%; -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    animation: gradientShift 10s ease infinite;
  }
  @keyframes gradientShift {
    0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; }
  }
  .back-button {
      color: #1db954;
      font-size: 18px;
      margin-right: 20px;
  }
  .back-button i { margin-right: 5px; }

  /* Detail Page Specific Styles */
  .movie-detail-container {
    max-width: 900px;
    margin: 20px auto;
    padding: 20px;
    background: #181818;
    border-radius: 8px;
    box-shadow: 0 0 15px rgba(0,0,0,0.7);
    display: flex;
    flex-direction: column; /* Stack vertically on small screens */
    gap: 20px;
  }
  .detail-poster {
    width: 100%;
    max-width: 300px; /* Limit poster width */
    height: auto;
    border-radius: 8px;
    box-shadow: 0 0 10px rgba(0,0,0,0.5);
    align-self: center; /* Center poster when stacked */
  }
  .detail-info {
    flex-grow: 1;
  }
  .detail-title {
    font-size: 32px;
    font-weight: 700;
    margin: 0 0 10px 0;
    color: #1db954;
  }
  .detail-year {
    font-size: 18px;
    color: #aaa;
    margin-bottom: 15px;
  }
  .detail-overview {
    font-size: 16px;
    line-height: 1.6;
    color: #ccc;
    margin-bottom: 25px;
  }
  .detail-quality {
      display: inline-block;
      background: #1db954;
      color: #000;
      font-weight: 700;
      padding: 5px 10px;
      border-radius: 5px;
      margin-bottom: 20px;
      text-transform: uppercase;
  }
  .detail-quality.trending {
    background: linear-gradient(45deg, #ff0077, #ff9900);
    color: #fff;
  }

  .action-buttons {
    display: flex;
    gap: 15px;
    flex-wrap: wrap; /* Allow buttons to wrap on smaller screens */
  }
  .action-button {
    flex: 1; /* Allow buttons to grow and shrink */
    min-width: 150px; /* Minimum width for buttons */
    padding: 12px 20px;
    border-radius: 8px;
    text-align: center;
    font-size: 18px;
    font-weight: 700;
    transition: background 0.3s ease;
  }
  .watch-button {
    background: #1db954;
    color: #000;
  }
  .watch-button:hover {
    background: #17a34a;
  }
  .download-button {
    background: #007bff; /* Blue for download */
    color: #fff;
  }
  .download-button:hover {
    background: #0056b3;
  }
  /* Fallback for no link */
  .no-link-message {
      color: #999;
      font-size: 14px;
      margin-top: 10px;
  }

  /* Mobile adjustments */
  @media (min-width: 769px) { /* On larger screens, display side-by-side */
      .movie-detail-container {
          flex-direction: row;
      }
      .detail-poster {
          margin-right: 30px; /* Space between poster and info */
          align-self: flex-start; /* Align poster to top */
      }
  }

  @media (max-width: 768px) {
    header { padding: 8px 15px; }
    header h1 { font-size: 20px; }
    .back-button { font-size: 16px; }
    .movie-detail-container { padding: 15px; margin: 15px auto; }
    .detail-poster { max-width: 200px; } /* Smaller poster on mobile */
    .detail-title { font-size: 24px; }
    .detail-year { font-size: 16px; }
    .detail-overview { font-size: 14px; }
    .detail-quality { font-size: 12px; padding: 3px 8px; }
    .action-button { font-size: 16px; padding: 10px 15px; }
  }

  /* Bottom nav for consistency (same as index_html) */
  .bottom-nav {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: #181818; display: flex; justify-content: space-around;
    padding: 10px 0; box-shadow: 0 -2px 5px rgba(0,0,0,0.7); z-index: 200;
  }
  .nav-item {
    display: flex; flex-direction: column; align-items: center;
    color: #ccc; font-size: 12px; text-align: center; transition: color 0.2s ease;
  }
  .nav-item:hover { color: #1db954; }
  .nav-item i { font-size: 24px; margin-bottom: 4px; }
  @media (max-width: 768px) {
      .bottom-nav { padding: 8px 0; }
      .nav-item { font-size: 10px; }
      .nav-item i { font-size: 20px; margin-bottom: 2px; }
  }
</style>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
</head>
<body>
<header>
  <a href="{{ url_for('home') }}" class="back-button"><i class="fas fa-arrow-left"></i>Back</a>
  <h1>Movie Dokan</h1>
</header>
<main>
  {% if movie %}
  <div class="movie-detail-container">
    {% if movie.poster %}
      <img class="detail-poster" src="{{ movie.poster }}" alt="{{ movie.title }}">
    {% else %}
      <div class="detail-poster" style="background:#333; display:flex;align-items:center;justify-content:center;color:#777; font-size:18px;">
        No Image
      </div>
    {% endif %}
    <div class="detail-info">
      <h2 class="detail-title">{{ movie.title }}</h2>
      <div class="detail-year">{{ movie.year }}</div>
      {% if movie.quality %}
        <div class="detail-quality {% if movie.quality == 'TRENDING' %}trending{% endif %}">{{ movie.quality }}</div>
      {% endif %}
      <p class="detail-overview">{{ movie.overview }}</p>
      
      <div class="action-buttons">
        {% if movie.link %}
          <a class="action-button watch-button" href="{{ movie.link }}" target="_blank" rel="noopener">▶ Watch Now</a>
          {# You can add a separate download link if your 'link' sometimes means download #}
          {# <a class="action-button download-button" href="{{ movie.link }}" target="_blank" rel="noopener">⇩ Download</a> #}
        {% else %}
          <p class="no-link-message">No watch/download link available yet.</p>
        {% endif %}
      </div>
    </div>
  </div>
  {% else %}
    <p style="text-align:center; color:#999; margin-top: 40px;">Movie not found.</p>
  {% endif %}
</main>
<nav class="bottom-nav">
  <a href="{{ url_for('home') }}" class="nav-item">
    <i class="fas fa-home"></i>
    <span>Home</span>
  </a>
  <a href="#" class="nav-item">
    <i class="fas fa-film"></i>
    <span>Movie</span>
  </a>
  <a href="{{ url_for('admin') }}" class="nav-item">
    <i class="fas fa-plus-circle"></i>
    <span>Request</span>
  </a>
  <a href="#" class="nav-item">
    <i class="fas fa-tv"></i>
    <span>Web Series</span>
  </a>
  <a href="#" class="nav-item">
    <i class="fas fa-search"></i>
    <span>Search</span>
  </a>
</nav>
</body>
</html>
"""

# --- admin_html remains unchanged from previous version ---
admin_html = """
<!DOCTYPE html>
<html>
<head>
  <title>Admin Panel - Movie Dokan</title>
  <style>
    body { font-family: Arial, sans-serif; background: #121212; color: #eee; padding: 20px; }
    h2 { 
      /* RGB Light Effect for Admin Title */
      background: linear-gradient(270deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3);
      background-size: 400% 400%;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: gradientShift 10s ease infinite; /* Slower animation */
      display: inline-block; /* Required for background-clip: text to work on h2 */
      font-size: 28px;
    }
    @keyframes gradientShift {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
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
    <input name="quality" placeholder="Quality tag (e.g. HD, Hindi Dubbed, TRENDING)" />
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
    
    movies_list = list(result)
    # Ensure _id is converted to string for URL generation
    for movie in movies_list:
        movie['_id'] = str(movie['_id']) 
    return render_template_string(index_html, movies=movies_list, query=query)

# --- New Route for Movie Details ---
@app.route('/movie/<movie_id>')
def movie_detail(movie_id):
    try:
        # Fetch movie from MongoDB using its _id
        movie = movies.find_one({"_id": ObjectId(movie_id)})
        if movie:
            # Convert _id to string for template
            movie['_id'] = str(movie['_id'])
        return render_template_string(detail_html, movie=movie)
    except Exception as e:
        print(f"Error fetching movie detail for ID {movie_id}: {e}")
        return render_template_string(detail_html, movie=None) # Or render an error page

@app.route('/admin', methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        title = request.form.get("title")
        link = request.form.get("link")
        quality = request.form.get("quality", "").upper()
        
        movie_data = {
            "title": title,
            "link": link or "",
            "quality": quality,
            "overview": "No overview available.",
            "poster": "",
            "year": "N/A"
        }

        if TMDB_API_KEY:
            tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
            try:
                res = requests.get(tmdb_url, timeout=5).json()
                if res and "results" in res and res["results"]:
                    data = res["results"][0]
                    movie_data["title"] = data.get("title", title)
                    movie_data["overview"] = data.get("overview", "No overview available.")
                    movie_data["poster"] = f"https://image.tmdb.org/t/p/w500{data['poster_path']}" if data.get("poster_path") else ""
                    movie_data["year"] = data.get("release_date", "")[:4]
                else:
                    print(f"No results found on TMDb for title: {title}")
            except requests.exceptions.RequestException as e:
                print(f"Error connecting to TMDb API for '{title}': {e}")
            except Exception as e:
                print(f"An unexpected error occurred while fetching TMDb data: {e}")
        else:
            print("TMDB_API_KEY not set. Skipping TMDb API call.")

        try:
            movies.insert_one(movie_data)
            print(f"Movie '{movie_data['title']}' added successfully!")
            return redirect(url_for('admin')) # Use url_for for robustness
        except Exception as e:
            print(f"Error inserting movie into MongoDB: {e}")
            return render_template_string(admin_html, error="Failed to add movie.")

    return render_template_string(admin_html)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
