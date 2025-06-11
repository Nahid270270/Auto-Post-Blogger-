from flask import Flask, render_template_string, request, redirect
from pymongo import MongoClient
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

# --- Updated index_html with RGB Title Effect ---
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
    /* RGB Light Effect */
    background: linear-gradient(270deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3);
    background-size: 400% 400%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradientShift 10s ease infinite; /* Slower animation */
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
    background: #fff; /* Changed search box to white */
    color: #333;
  }
  input[type="search"]::placeholder {
      color: #999;
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
    height: 270px; /* Ensure consistent height for all posters */
    object-fit: cover; /* Cover the area without stretching */
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
    background: #1db954; /* Default for quality */
    color: #000;
    font-weight: 700;
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    user-select: none;
  }
  /* Specific style for "Trending" badge */
  .badge.trending {
    background: linear-gradient(45deg, #ff0077, #ff9900); /* Red-Orange gradient for trending */
    color: #fff;
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

  /* Added for "Trending on MovieDokan" style */
  .trending-header {
      color: #fff;
      font-size: 22px;
      font-weight: 700;
      padding: 10px 15px;
      background: linear-gradient(90deg, #e44d26, #f16529); /* Orange gradient */
      border-radius: 5px;
      margin-bottom: 25px;
      text-align: center;
      box-shadow: 0 2px 10px rgba(0,0,0,0.5);
  }
  .trending-header::before {
      content: '🔥'; /* Fire emoji */
      margin-right: 10px;
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
    header h1 {
        font-size: 20px;
    }
    input[type="search"] {
        max-width: unset;
        font-size: 14px;
    }
    .trending-header {
        font-size: 18px;
    }
  }

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
  .nav-item img { /* If using image icons */
      width: 24px;
      height: 24px;
      margin-bottom: 4px;
      filter: invert(0.8); /* Adjust for light icons on dark background */
  }
  .nav-item:hover img {
      filter: invert(1) drop-shadow(0 0 5px #1db954); /* Highlight icon on hover */
  }
  /* Using Font Awesome for icons (requires linking CDN in <head>) */
  .nav-item i {
      font-size: 24px;
      margin-bottom: 4px;
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
    <div class="movie-card">
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

<nav class="bottom-nav">
  <a href="#" class="nav-item">
    <i class="fas fa-home"></i>
    <span>Home</span>
  </a>
  <a href="#" class="nav-item">
    <i class="fas fa-film"></i>
    <span>Movie</span>
  </a>
  <a href="#" class="nav-item">
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

# --- Updated admin_html with RGB Title Effect ---
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
        # Using regex for case-insensitive search
        result = movies.find({"title": {"$regex": query, "$options": "i"}})
    else:
        # Fetching latest 30 movies, you might want a more complex sorting
        result = movies.find().sort('_id', -1).limit(30)
    
    # Convert cursor to list for render_template_string
    movies_list = list(result)
    return render_template_string(index_html, movies=movies_list, query=query)

@app.route('/admin', methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        title = request.form.get("title")
        link = request.form.get("link")
        quality = request.form.get("quality", "").upper() # Ensure quality is uppercase
        
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
                res = requests.get(tmdb_url, timeout=5).json() # Added timeout
                if res and "results" in res and res["results"]:
                    data = res["results"][0]
                    movie_data["title"] = data.get("title", title) # Use TMDb title if available
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
            return redirect('/admin')
        except Exception as e:
            print(f"Error inserting movie into MongoDB: {e}")
            # Optionally, render admin_html with an error message
            return render_template_string(admin_html, error="Failed to add movie.")

    return render_template_string(admin_html)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True) # Added debug=True for development
