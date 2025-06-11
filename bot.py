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

# --- index_html (remains unchanged) ---
index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>MovieZone</title>
<style>
  /* Reset & basics */
  * {
    box-sizing: border-box;
  }
  body {
    margin: 0; background: #121212; color: #eee;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    -webkit-tap-highlight-color: transparent; /* Remove tap highlight on mobile */
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
    cursor: pointer;
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

  .overview { display: none; } /* Overview hidden by default in card view */

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
    <a href="{{ url_for('movie_detail', movie_id=m._id) }}" class="movie-card">
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

# --- Updated detail_html template ---
detail_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{{ movie.title if movie else "Movie Not Found" }} - Movie Details</title>
<style>
  /* General styles (similar to index_html for consistency) */
  * { box-sizing: border-box; }
  body { margin: 0; background: #121212; color: #eee; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
  a { text-decoration: none; color: inherit; }
  a:hover { color: #1db954; }

  header {
    position: sticky; top: 0; left: 0; right: 0;
    background: #181818; padding: 10px 20px;
    display: flex; justify-content: flex-start; align-items: center; z-index: 100;
    box-shadow: 0 2px 5px rgba(0,0,0,0.7);
  }
  header h1 {
    margin: 0; font-weight: 700; font-size: 24px;
    background: linear-gradient(270deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3);
    background-size: 400% 400%; -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    animation: gradientShift 10s ease infinite;
    flex-grow: 1; /* Allow title to take available space */
    text-align: center;
  }
  @keyframes gradientShift {
    0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; }
  }
  .back-button {
      color: #1db954;
      font-size: 18px;
      position: absolute; /* Position absolutely to allow h1 to center */
      left: 20px;
      z-index: 101; /* Ensure back button is above header h1 if overlapping */
  }
  .back-button i { margin-right: 5px; }

  /* Detail Page Specific Styles */
  .movie-detail-container {
    max-width: 1000px; /* Wider container */
    margin: 20px auto;
    padding: 25px;
    background: #181818;
    border-radius: 8px;
    box-shadow: 0 0 15px rgba(0,0,0,0.7);
    display: flex;
    flex-direction: column; /* Default for small screens */
    gap: 25px; /* More space */
  }

  .main-info {
      display: flex;
      flex-direction: column; /* Stack poster and info on mobile */
      gap: 25px;
  }

  .detail-poster-wrapper {
      position: relative;
      width: 100%;
      max-width: 300px; /* Limit poster width */
      flex-shrink: 0; /* Prevent poster from shrinking */
      align-self: center; /* Center poster when stacked */
  }
  .detail-poster {
    width: 100%;
    height: auto;
    border-radius: 8px;
    box-shadow: 0 0 10px rgba(0,0,0,0.5);
    display: block;
  }
  .detail-poster-wrapper .badge {
      position: absolute;
      top: 10px;
      left: 10px;
      font-size: 14px;
      padding: 4px 8px;
      border-radius: 5px;
  }

  .detail-info {
    flex-grow: 1;
  }
  .detail-title {
    font-size: 38px; /* Larger title */
    font-weight: 700;
    margin: 0 0 10px 0;
    color: #eee; /* White title for better contrast */
    text-shadow: 0 0 5px rgba(0,0,0,0.5);
  }
  .detail-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 15px;
      margin-bottom: 20px;
      font-size: 16px;
      color: #ccc;
  }
  .detail-meta span {
      background: #282828;
      padding: 5px 10px;
      border-radius: 5px;
      white-space: nowrap;
  }
  .detail-meta strong {
      color: #fff;
  }

  .detail-overview {
    font-size: 17px; /* Slightly larger overview text */
    line-height: 1.7;
    color: #ccc;
    margin-bottom: 30px; /* More space below overview */
  }

  .action-buttons {
    display: flex;
    gap: 20px; /* More space between buttons */
    justify-content: center; /* Center buttons */
    flex-wrap: wrap;
    margin-top: 20px; /* Ensure spacing from overview */
  }
  .action-button {
    flex: 1;
    min-width: 200px; /* Wider buttons */
    padding: 15px 20px; /* Larger padding */
    border-radius: 8px;
    text-align: center;
    font-size: 20px; /* Larger font */
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
    background: #e44d26; /* Orange for download */
    color: #fff;
  }
  .download-button:hover {
    background: #d43d16;
  }
  .no-link-message {
      color: #999;
      font-size: 16px;
      text-align: center;
      width: 100%;
  }

  /* Responsive Adjustments for Detail Page */
  @media (min-width: 769px) { /* On larger screens, display side-by-side */
      .main-info {
          flex-direction: row; /* Poster and info side-by-side */
          align-items: flex-start; /* Align to top */
      }
      .detail-poster-wrapper {
          margin-right: 40px; /* Space between poster and info */
      }
      .detail-title {
          font-size: 44px; /* Even larger title on desktop */
      }
      .action-buttons {
          justify-content: flex-start; /* Align buttons to left on desktop */
      }
  }

  @media (max-width: 768px) {
    header h1 { font-size: 20px; margin: 0; }
    .back-button { font-size: 16px; left: 15px; }
    .movie-detail-container { padding: 15px; margin: 15px auto; gap: 15px; }
    .main-info { gap: 15px; }
    .detail-poster-wrapper { max-width: 180px; } /* Smaller poster on mobile */
    .detail-poster-wrapper .badge { font-size: 12px; padding: 2px 6px; top: 8px; left: 8px; }
    .detail-title { font-size: 28px; }
    .detail-meta { font-size: 14px; gap: 10px; margin-bottom: 15px; }
    .detail-overview { font-size: 15px; margin-bottom: 20px; }
    .action-button { font-size: 16px; padding: 12px 15px; min-width: 120px; gap: 10px; }
  }

  @media (max-width: 480px) {
      .detail-title { font-size: 22px; }
      .detail-meta { font-size: 13px; }
      .detail-overview { font-size: 14px; }
      .action-button { font-size: 14px; padding: 10px 12px; min-width: unset; flex: 1 1 45%; } /* Two columns on very small screens */
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
    <div class="main-info">
        <div class="detail-poster-wrapper">
            {% if movie.poster %}
              <img class="detail-poster" src="{{ movie.poster }}" alt="{{ movie.title }}">
            {% else %}
              <div class="detail-poster" style="background:#333; display:flex;align-items:center;justify-content:center;color:#777; font-size:18px; min-height: 250px;">
                No Image
              </div>
            {% endif %}
            {% if movie.quality %}
              <div class="badge {% if movie.quality == 'TRENDING' %}trending{% endif %}">{{ movie.quality }}</div>
            {% endif %}
        </div>
        <div class="detail-info">
          <h2 class="detail-title">{{ movie.title }}</h2>
          <div class="detail-meta">
              {% if movie.release_date %}<span><strong>Release:</strong> {{ movie.release_date }}</span>{% endif %}
              {% if movie.vote_average %}<span><strong>Rating:</strong> {{ "%.1f"|format(movie.vote_average) }}/10 <i class="fas fa-star" style="color:#FFD700;"></i></span>{% endif %}
              {% if movie.original_language %}<span><strong>Language:</strong> {{ movie.original_language | upper }}</span>{% endif %}
              {% if movie.genres %}<span><strong>Genres:</strong> {{ movie.genres | join(', ') }}</span>{% endif %}
          </div>
          <p class="detail-overview">{{ movie.overview }}</p>
        </div>
    </div>
    
    <div class="action-buttons">
      {% if movie.link %}
        <a class="action-button watch-button" href="{{ movie.link }}" target="_blank" rel="noopener">▶ Watch Now</a>
        {# You can add a separate download link if your 'link' sometimes means download, or rename 'link' field in DB to 'watch_link' #}
        {# Example: <a class="action-button download-button" href="{{ movie.download_link }}" target="_blank" rel="noopener">⇩ Download</a> #}
      {% else %}
        <p class="no-link-message">No watch/download link available yet.</p>
      {% endif %}
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

# --- admin_html (remains unchanged) ---
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
    for movie in movies_list:
        movie['_id'] = str(movie['_id']) 
    return render_template_string(index_html, movies=movies_list, query=query)

@app.route('/movie/<movie_id>')
def movie_detail(movie_id):
    try:
        movie = movies.find_one({"_id": ObjectId(movie_id)})
        if movie:
            movie['_id'] = str(movie['_id'])
            
            # Fetch additional details from TMDb if not already stored
            # Or always fetch fresh details for the detail page
            if TMDB_API_KEY:
                # Use TMDb movie ID if available, otherwise search again
                tmdb_id = movie.get("tmdb_id") 
                if tmdb_id:
                    tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
                else: # Fallback: search by title if tmdb_id is not stored
                    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie['title']}"
                    search_res = requests.get(search_url, timeout=5).json()
                    if search_res and "results" in search_res and search_res["results"]:
                        tmdb_id = search_res["results"][0].get("id")
                        tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
                    else:
                        tmdb_url = None # No TMDb ID found

                if tmdb_url:
                    try:
                        res = requests.get(tmdb_url, timeout=5).json()
                        if res:
                            # Update movie object with more details from TMDb
                            movie["overview"] = res.get("overview", movie.get("overview", "No overview available."))
                            movie["poster"] = f"https://image.tmdb.org/t/p/w500{res['poster_path']}" if res.get("poster_path") else movie.get("poster", "")
                            movie["release_date"] = res.get("release_date", movie.get("year", "N/A"))
                            movie["vote_average"] = res.get("vote_average")
                            movie["original_language"] = res.get("original_language")
                            movie["genres"] = [g["name"] for g in res.get("genres", [])]
                            # Store the TMDb ID for future direct access
                            movies.update_one({"_id": ObjectId(movie_id)}, {"$set": {"tmdb_id": tmdb_id}})
                    except requests.exceptions.RequestException as e:
                        print(f"Error connecting to TMDb API for detail '{movie_id}': {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred while fetching TMDb detail data: {e}")
            else:
                print("TMDB_API_KEY not set. Cannot fetch additional details.")

        return render_template_string(detail_html, movie=movie)
    except Exception as e:
        print(f"Error fetching movie detail for ID {movie_id}: {e}")
        return render_template_string(detail_html, movie=None)

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
            "year": "N/A", # Keep year for initial display
            "release_date": "N/A", # Full release date
            "vote_average": None,
            "original_language": "N/A",
            "genres": [],
            "tmdb_id": None # Store TMDb ID
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
                    movie_data["year"] = data.get("release_date", "")[:4] # Keep for card view
                    movie_data["release_date"] = data.get("release_date", "N/A") # Full date
                    movie_data["vote_average"] = data.get("vote_average")
                    movie_data["original_language"] = data.get("original_language", "N/A")
                    movie_data["genres"] = [g["name"] for g in data.get("genre_ids", []) if g in TMDb_Genre_Map] # Map genre IDs to names
                    movie_data["tmdb_id"] = data.get("id") # Store TMDb ID
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
            return redirect(url_for('admin'))
        except Exception as e:
            print(f"Error inserting movie into MongoDB: {e}")
            return render_template_string(admin_html, error="Failed to add movie.")

    return render_template_string(admin_html)

# TMDb Genre Map (for converting genre IDs to names) - Add this at the top of your file
TMDb_Genre_Map = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
