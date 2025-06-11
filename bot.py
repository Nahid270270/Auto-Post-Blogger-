from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests, os

app = Flask(__name__)

# Environment variables for MongoDB URI and TMDb API Key
MONGO_URI = os.getenv("MONGO_URI")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Check if environment variables are set
if not MONGO_URI:
    print("Error: MONGO_URI environment variable not set. Exiting.")
    exit(1)
if not TMDB_API_KEY:
    print("Error: TMDB_API_KEY environment variable not set. Exiting.")
    exit(1)

# Database connection
try:
    client = MongoClient(MONGO_URI)
    db = client["movie_db"]
    movies = db["movies"]
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}. Exiting.")
    exit(1)

# TMDb Genre Map (for converting genre IDs to names)
TMDb_Genre_Map = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10402: "Music", 9648: "Mystery",
    10749: "Romance", 878: "Science Fiction", 10770: "TV Movie", 53: "Thriller",
    10752: "War", 37: "Western", 10751: "Family", 14: "Fantasy", 36: "History"
}

# --- START OF index_html TEMPLATE ---
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
    margin: 0;
    padding: 0;
  }
  body {
    background: #121212; /* Dark background */
    color: #eee;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    -webkit-tap-highlight-color: transparent;
  }
  a { text-decoration: none; color: inherit; }
  a:hover { color: #1db954; } /* Adjusted hover color */
  
  /* Header Styles */
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
    background: linear-gradient(270deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3); /* RGB gradient for title */
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
    margin-left: 20px; /* Space between title and search */
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

  /* Main Content Area */
  main {
    max-width: 1200px; /* Max width for content */
    margin: 20px auto;
    padding: 0 15px;
    padding-bottom: 70px; /* Space for bottom nav */
  }

  /* Movie Grid and Card Styles */
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill,minmax(180px,1fr)); /* Default: around 3-4 columns */
    gap: 20px;
  }
  .movie-card {
    background: #181818; /* Dark card background */
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 0 8px rgba(0,0,0,0.6);
    transition: transform 0.2s ease;
    position: relative;
    cursor: pointer;
    border: 2px solid transparent; /* Initial transparent border for smooth transition */
  }
  /* RGB border animation on hover */
  .movie-card:hover {
    transform: scale(1.05); /* Slight zoom on hover */
    /* RGB Border Gradient Animation */
    border: 2px solid;
    border-image: linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet) 1;
    animation: rgbBorder 3s linear infinite; /* Animates the border gradient */
    box-shadow: 0 0 15px rgba(0,0,0,0.8); /* Maintain shadow on hover */
  }
  @keyframes rgbBorder {
    0% { border-image: linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet) 1; }
    16.67% { border-image: linear-gradient(to right, orange, yellow, green, blue, indigo, violet, red) 1; }
    33.33% { border-image: linear-gradient(to right, yellow, green, blue, indigo, violet, red, orange) 1; }
    50% { border-image: linear-gradient(to right, green, blue, indigo, violet, red, orange, yellow) 1; }
    66.67% { border-image: linear-gradient(to right, blue, indigo, violet, red, orange, yellow, green) 1; }
    83.33% { border-image: linear-gradient(to right, indigo, violet, red, orange, yellow, green, blue) 1; }
    100% { border-image: linear-gradient(to right, violet, red, orange, yellow, green, blue, indigo) 1; }
  }

  .movie-poster {
    width: 100%;
    height: 270px; /* Standard poster height */
    object-fit: cover;
    display: block;
  }
  .movie-info {
    padding: 10px;
    background: rgba(0, 0, 0, 0.7); /* Translucent background for text */
    position: absolute; /* Position over the poster */
    bottom: 0;
    left: 0;
    right: 0;
    text-align: center; /* Center text */
  }
  .movie-title {
    font-size: 18px;
    font-weight: 700;
    margin: 0 0 4px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #007bff; /* Blue for title, as in MovieDokan screenshot */
  }
  .movie-year {
    font-size: 14px;
    color: #ff8c00; /* Orange for year, as in MovieDokan screenshot */
    margin-bottom: 6px;
  }

  /* Badge Styles (for Quality & Trending) */
  .badge {
    position: absolute;
    top: 8px; /* Offset from top */
    right: 8px; /* Offset from right */
    background: #1db954; /* Default green for quality */
    color: #000;
    font-weight: 700;
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    user-select: none;
    z-index: 10; /* Ensure it's above poster */
    /* Skew/Rotate for "Trending" badge */
    transform: rotate(45deg);
    transform-origin: top right;
    right: -20px; /* Adjust to move it out partially */
    top: 15px; /* Adjust vertical position */
    width: 100px; /* Fixed width to ensure consistent angle */
    text-align: center;
    box-shadow: 0 2px 5px rgba(0,0,0,0.5);
  }
  .badge.trending {
    background: linear-gradient(45deg, #ff0077, #ff9900); /* Red-Orange gradient for trending */
    color: #fff;
    padding: 4px 15px; /* Larger padding for trending tag */
    font-size: 11px;
    letter-spacing: 1px;
  }
  .badge.trending::before {
      content: ''; /* No extra content needed for this style */
  }

  .overview { display: none; } /* Overview hidden by default in card view */

  /* Trending Header */
  .trending-header {
      color: #fff;
      font-size: 22px;
      font-weight: 700;
      padding: 10px 15px;
      background: linear-gradient(90deg, #e44d26, #f16529); /* Orange/red gradient */
      border-radius: 5px;
      margin-bottom: 25px;
      text-align: center;
      box-shadow: 0 2px 10px rgba(0,0,0,0.5);
  }
  .trending-header::before {
      content: '🔥'; /* Fire emoji */
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
    .grid { 
        grid-template-columns: repeat(auto-fill,minmax(90px,1fr)); /* 3 columns on mobile (approx. 90px width) */
        gap: 10px;
    }
    .movie-card { box-shadow: 0 0 5px rgba(0,0,0,0.5); }
    .movie-poster { height: 130px; } /* Smaller height for mobile posters */
    .movie-info { padding: 8px; background: rgba(0, 0, 0, 0.7); }
    .movie-title { font-size: 12px; margin: 0 0 2px 0; }
    .movie-year { font-size: 10px; margin-bottom: 4px; }
    .badge { 
        font-size: 9px; padding: 1px 4px; top: 5px; right: -15px; /* Adjust for smaller screens */
        transform: rotate(45deg); /* Keep rotation */
        width: 80px; /* Smaller width for mobile badge */
    }
  }

  @media (max-width: 480px) {
      .grid { grid-template-columns: repeat(auto-fill,minmax(80px,1fr)); } /* Even smaller min width for very small screens */
      .movie-poster { height: 110px; }
  }
  /* Mobile adjustments - END */

  /* Bottom Navigation Bar Styles (based on screenshot) */
  .bottom-nav {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: #1f1f1f; /* Slightly lighter dark for nav */
    display: flex; justify-content: space-around;
    padding: 10px 0;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.8);
    z-index: 200;
  }
  .nav-item {
    display: flex; flex-direction: column; align-items: center;
    color: #ccc; /* Default color for icons/text */
    font-size: 12px;
    text-align: center;
    transition: color 0.2s ease;
  }
  .nav-item:hover, .nav-item.active { /* Active state for Home */
    color: #e44d26; /* Orange color for active/hover */
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
  <a href="{{ url_for('home') }}" class="nav-item {% if request.endpoint == 'home' and not request.args.get('q') %}active{% endif %}">
    <i class="fas fa-home"></i>
    <span>Home</span>
  </a>
  <a href="{{ url_for('movies_only') }}" class="nav-item {% if request.endpoint == 'movies_only' %}active{% endif %}">
    <i class="fas fa-film"></i>
    <span>Movie</span>
  </a>
  <a href="https://t.me/Movie_Request_Group_23" class="nav-item" target="_blank" rel="noopener">
    <i class="fas fa-plus-circle"></i>
    <span>Request</span>
  </a>
  <a href="{{ url_for('webseries') }}" class="nav-item {% if request.endpoint == 'webseries' %}active{% endif %}">
    <i class="fas fa-tv"></i>
    <span>Web Series</span>
  </a>
  <a href="{{ url_for('home') }}" class="nav-item {% if request.args.get('q') %}active{% endif %}">
    <i class="fas fa-search"></i>
    <span>Search</span>
  </a>
</nav>
</body>
</html>
"""
# --- END OF index_html TEMPLATE ---


# --- START OF detail_html TEMPLATE ---
detail_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{{ movie.title if movie else "Movie Not Found" }} - Movie Details</title>
<style>
  /* General styles (similar to index_html for consistency) */
  * { box-sizing: border-box; margin: 0; padding: 0;}
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
    flex-grow: 1;
    text-align: center;
  }
  @keyframes gradientShift {
    0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; }
  }
  .back-button {
      color: #1db954;
      font-size: 18px;
      position: absolute;
      left: 20px;
      z-index: 101;
  }
  .back-button i { margin-right: 5px; }

  /* Detail Page Specific Styles */
  .movie-detail-container {
    max-width: 1000px;
    margin: 20px auto;
    padding: 25px;
    background: #181818;
    border-radius: 8px;
    box-shadow: 0 0 15px rgba(0,0,0,0.7);
    display: flex;
    flex-direction: column;
    gap: 25px;
  }

  .main-info {
      display: flex;
      flex-direction: column;
      gap: 25px;
  }

  .detail-poster-wrapper {
      position: relative;
      width: 100%;
      max-width: 300px;
      flex-shrink: 0;
      align-self: center;
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
      background: #1db954; /* Consistent badge color */
      color: #000;
      font-weight: 700;
      text-transform: uppercase;
  }
  .detail-poster-wrapper .badge.trending {
    background: linear-gradient(45deg, #ff0077, #ff9900);
    color: #fff;
  }

  .detail-info {
    flex-grow: 1;
  }
  .detail-title {
    font-size: 38px;
    font-weight: 700;
    margin: 0 0 10px 0;
    color: #eee;
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
    font-size: 17px;
    line-height: 1.7;
    color: #ccc;
    margin-bottom: 30px;
  }

  /* --- DOWNLOAD LINKS SECTION --- */
  .download-section {
    width: 100%;
    text-align: center;
    margin-top: 30px;
    background: #1f1f1f;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 0 10px rgba(0,0,0,0.5);
  }
  .download-section h3 {
    font-size: 24px;
    font-weight: 700;
    color: #00ff00; /* Green color for heading */
    margin-bottom: 20px;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
  }
  .download-section h3::before,
  .download-section h3::after {
    content: '[↓]';
    color: #00ff00;
    font-size: 20px;
  }

  .download-item {
    margin-bottom: 15px;
  }
  .download-quality-info {
    font-size: 18px;
    color: #ff9900; /* Orange color for quality info */
    margin-bottom: 10px;
    font-weight: 600;
  }
  .download-button-wrapper {
    width: 100%;
    max-width: 300px; /* Limit button width */
    margin: 0 auto;
  }
  .download-button {
    display: block; /* Make button full width of its wrapper */
    padding: 12px 20px;
    border-radius: 30px; /* Pill shape */
    background: linear-gradient(to right, #6a0dad, #8a2be2, #4b0082); /* Purple gradient */
    color: #fff;
    font-size: 18px;
    font-weight: 700;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    border: none;
  }
  .download-button:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 15px rgba(0,0,0,0.7);
    background: linear-gradient(to right, #7b2dfc, #9a4beb, #5c1bb2); /* Slightly brighter purple */
  }

  .no-link-message {
      color: #999;
      font-size: 16px;
      text-align: center;
      width: 100%;
      padding: 20px;
      background: #1f1f1f;
      border-radius: 8px;
  }


  /* Responsive Adjustments for Detail Page */
  @media (min-width: 769px) {
      .main-info {
          flex-direction: row;
          align-items: flex-start;
      }
      .detail-poster-wrapper {
          margin-right: 40px;
      }
      .detail-title {
          font-size: 44px;
      }
      /* No direct "action-buttons" anymore, removed specific style */
  }

  @media (max-width: 768px) {
    header h1 { font-size: 20px; margin: 0; }
    .back-button { font-size: 16px; left: 15px; }
    .movie-detail-container { padding: 15px; margin: 15px auto; gap: 15px; }
    .main-info { gap: 15px; }
    .detail-poster-wrapper { max-width: 180px; }
    .detail-poster-wrapper .badge { font-size: 12px; padding: 2px 6px; top: 8px; left: 8px; }
    .detail-title { font-size: 28px; }
    .detail-meta { font-size: 14px; gap: 10px; margin-bottom: 15px; }
    .detail-overview { font-size: 15px; margin-bottom: 20px; }
    
    .download-section h3 { font-size: 20px; }
    .download-section h3::before,
    .download-section h3::after { font-size: 18px; }
    .download-quality-info { font-size: 16px; }
    .download-button { font-size: 16px; padding: 10px 15px; }
  }

  @media (max-width: 480px) {
      .detail-title { font-size: 22px; }
      .detail-meta { font-size: 13px; }
      .detail-overview { font-size: 14px; }
      .download-section h3 { font-size: 18px; }
      .download-section h3::before,
      .download-section h3::after { font-size: 16px; }
      .download-quality-info { font-size: 14px; }
      .download-button { font-size: 14px; padding: 8px 12px; }
  }

  /* Bottom nav for consistency (same as index_html) */
  .bottom-nav {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: #1f1f1f; display: flex; justify-content: space-around;
    padding: 10px 0; box-shadow: 0 -2px 5px rgba(0,0,0,0.7); z-index: 200;
  }
  .nav-item {
    display: flex; flex-direction: column; align-items: center;
    color: #ccc; font-size: 12px; text-align: center; transition: color 0.2s ease;
  }
  .nav-item:hover { color: #e44d26; } /* Orange color for active/hover */
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
    
    <div class="download-section">
      <h3>Download Links</h3>
      {% if movie.links and movie.links|length > 0 %}
        {% for link_item in movie.links %}
        <div class="download-item">
          <p class="download-quality-info">({{ link_item.quality }}) [{{ link_item.size }}]</p>
          <div class="download-button-wrapper">
            <a class="download-button" href="{{ link_item.url }}" target="_blank" rel="noopener">Download</a>
          </div>
        </div>
        {% endfor %}
      {% else %}
        <p class="no-link-message">No download links available yet.</p>
      {% endif %}
    </div>

  </div>
  {% else %}
    <p style="text-align:center; color:#999; margin-top: 40px;">Movie not found.</p>
  {% endif %}
</main>
<nav class="bottom-nav">
  <a href="{{ url_for('home') }}" class="nav-item {% if request.endpoint == 'home' and not request.args.get('q') %}active{% endif %}">
    <i class="fas fa-home"></i>
    <span>Home</span>
  </a>
  <a href="{{ url_for('movies_only') }}" class="nav-item {% if request.endpoint == 'movies_only' %}active{% endif %}">
    <i class="fas fa-film"></i>
    <span>Movie</span>
  </a>
  <a href="https://t.me/Movie_Request_Group_23" class="nav-item" target="_blank" rel="noopener">
    <i class="fas fa-plus-circle"></i>
    <span>Request</span>
  </a>
  <a href="{{ url_for('webseries') }}" class="nav-item {% if request.endpoint == 'webseries' %}active{% endif %}">
    <i class="fas fa-tv"></i>
    <span>Web Series</span>
  </a>
  <a href="{{ url_for('home') }}" class="nav-item {% if request.args.get('q') %}active{% endif %}">
    <i class="fas fa-search"></i>
    <span>Search</span>
  </a>
</nav>
</body>
</html>
"""
# --- END OF detail_html TEMPLATE ---


# --- START OF admin_html TEMPLATE ---
admin_html = """
<!DOCTYPE html>
<html>
<head>
  <title>Admin Panel - Movie Dokan</title>
  <style>
    body { font-family: Arial, sans-serif; background: #121212; color: #eee; padding: 20px; }
    h2 { 
      background: linear-gradient(270deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3);
      background-size: 400% 400%;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: gradientShift 10s ease infinite;
      display: inline-block;
      font-size: 28px;
      margin-bottom: 20px; /* Added margin */
    }
    @keyframes gradientShift {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    form { max-width: 600px; margin-bottom: 40px; border: 1px solid #333; padding: 20px; border-radius: 8px;}
    
    /* Input field specific styles */
    .form-group {
        margin-bottom: 15px;
    }
    .form-group label {
        display: block;
        margin-bottom: 5px;
        font-weight: bold;
        color: #ddd;
    }
    input[type="text"], input[type="url"], button {
      width: 100%;
      padding: 10px;
      margin-bottom: 15px; /* Adjust this if form-group already has margin */
      border-radius: 5px;
      border: none;
      font-size: 16px;
      background: #222;
      color: #eee;
    }
    /* Specific input for the link section */
    .link-input-group input[type="url"] {
        margin-bottom: 5px; /* Smaller margin between link inputs */
    }
    .link-input-group p {
        font-size: 14px;
        color: #bbb;
        margin-bottom: 5px;
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

    /* Styles for Movie List */
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
    }
    th, td {
        padding: 10px;
        text-align: left;
        border-bottom: 1px solid #333;
    }
    th {
        background: #282828;
        color: #eee;
    }
    td {
        background: #181818;
    }
    .delete-btn {
        background: #e44d26;
        color: #fff;
        padding: 5px 10px;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        transition: background 0.3s ease;
        font-size: 14px; /* Smaller font for table button */
        width: auto; /* Override full width */
        margin-bottom: 0; /* Remove bottom margin */
    }
    .delete-btn:hover {
        background: #d43d16;
    }
    .movie-list-container {
        max-width: 800px;
        margin-top: 40px;
        background: #181818;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 0 10px rgba(0,0,0,0.5);
    }
  </style>
</head>
<body>
  <h2>Add New Movie</h2>
  <form method="post">
    <div class="form-group">
        <label for="title">Movie Title:</label>
        <input type="text" name="title" id="title" placeholder="Movie Title" required />
    </div>

    <div class="form-group">
        <label>Download Links (only paste URL):</label>
        <div class="link-input-group">
            <p>480p Download Link [Approx. 590MB]:</p>
            <input type="url" name="link_480p" placeholder="Enter 480p download link" />
        </div>
        <div class="link-input-group">
            <p>720p Download Link [Approx. 1.4GB]:</p>
            <input type="url" name="link_720p" placeholder="Enter 720p download link" />
        </div>
        <div class="link-input-group">
            <p>1080p Download Link [Approx. 2.9GB]:</p>
            <input type="url" name="link_1080p" placeholder="Enter 1080p download link" />
        </div>
    </div>

    <div class="form-group">
        <label for="quality">Quality Tag (e.g., HD, Hindi Dubbed, TRENDING):</label>
        <input type="text" name="quality" id="quality" placeholder="Quality tag" />
    </div>
    
    <button type="submit">Add Movie</button>
  </form>

  <hr>

  <h2>Manage Existing Movies</h2>
  <div class="movie-list-container">
    {% if movies %}
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Quality</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for movie in movies %}
        <tr>
          <td>{{ movie.title }}</td>
          <td>{{ movie.quality }}</td>
          <td>
            <button class="delete-btn" onclick="confirmDelete('{{ movie._id }}', '{{ movie.title }}')">Delete</button>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p style="text-align:center; color:#999;">No movies found in the database.</p>
    {% endif %}
  </div>

  <script>
    function confirmDelete(movieId, movieTitle) {
      if (confirm('Are you sure you want to delete "' + movieTitle + '"?')) {
        window.location.href = '/delete_movie/' + movieId;
      }
    }
  </script>
</body>
</html>
"""
# --- END OF admin_html TEMPLATE ---

@app.route('/')
def home():
    query = request.args.get('q')
    if query:
        result = movies.find({"title": {"$regex": query, "$options": "i"}})
    else:
        # Fetch up to 30 latest movies, sorting by _id (which is usually insertion order)
        result = movies.find({"type": {"$ne": "series"}}).sort('_id', -1).limit(30) # Home shows movies, excluding series
    
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
            
            # Fetch additional details from TMDb if API key is available
            if TMDB_API_KEY:
                tmdb_id = movie.get("tmdb_id") 
                
                # If TMDb ID is not stored, search by title first
                if not tmdb_id:
                    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie['title']}"
                    try:
                        search_res = requests.get(search_url, timeout=5).json()
                        if search_res and "results" in search_res and search_res["results"]:
                            tmdb_id = search_res["results"][0].get("id")
                            # Update the movie in DB with tmdb_id for future faster access
                            movies.update_one({"_id": ObjectId(movie_id)}, {"$set": {"tmdb_id": tmdb_id}})
                        else:
                            print(f"No search results found on TMDb for title: {movie['title']}")
                            tmdb_id = None # Ensure tmdb_id is None if no search results
                    except requests.exceptions.RequestException as e:
                        print(f"Error connecting to TMDb API for search '{movie['title']}': {e}")
                        tmdb_id = None
                    except Exception as e:
                        print(f"An unexpected error occurred during TMDb search: {e}")
                        tmdb_id = None

                # If TMDb ID is found (either from DB or search), fetch full details
                if tmdb_id:
                    tmdb_detail_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
                    try:
                        res = requests.get(tmdb_detail_url, timeout=5).json()
                        if res:
                            movie["overview"] = res.get("overview", movie.get("overview", "No overview available."))
                            movie["poster"] = f"https://image.tmdb.org/t/p/w500{res['poster_path']}" if res.get("poster_path") else movie.get("poster", "")
                            movie["release_date"] = res.get("release_date", movie.get("year", "N/A"))
                            movie["vote_average"] = res.get("vote_average")
                            movie["original_language"] = res.get("original_language")
                            
                            genres_names = []
                            for genre_obj in res.get("genres", []):
                                if isinstance(genre_obj, dict) and genre_obj.get("id") in TMDb_Genre_Map:
                                    genres_names.append(TMDb_Genre_Map[genre_obj["id"]])
                            movie["genres"] = genres_names
                    except requests.exceptions.RequestException as e:
                        print(f"Error connecting to TMDb API for detail '{movie_id}': {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred while fetching TMDb detail data: {e}")
                else:
                    print(f"TMDb ID not found for movie '{movie.get('title', movie_id)}'. Skipping TMDb detail fetch.")
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
        quality_tag = request.form.get("quality", "").upper() # Renamed to avoid confusion with link quality
        
        # New: Collect links from individual input fields
        links_list = []
        
        link_480p = request.form.get("link_480p")
        if link_480p:
            links_list.append({"quality": "480p", "size": "590MB", "url": link_480p})
            
        link_720p = request.form.get("link_720p")
        if link_720p:
            links_list.append({"quality": "720p", "size": "1.4GB", "url": link_720p})
            
        link_1080p = request.form.get("link_1080p")
        if link_1080p:
            links_list.append({"quality": "1080p", "size": "2.9GB", "url": link_1080p})
        
        # Determine if it's a movie or web series. Default to movie.
        # You might want a dedicated field for this in admin_html later.
        # For now, let's assume if it has "Series" in title or quality tag, it's a series.
        content_type = "movie"
        if "SERIES" in title.upper() or "SERIES" in quality_tag.upper():
            content_type = "series"

        movie_data = {
            "title": title,
            "links": links_list, # This is now built from individual inputs
            "quality": quality_tag, # General quality tag
            "type": content_type, # New field for content type
            "overview": "No overview available.",
            "poster": "",
            "year": "N/A",
            "release_date": "N/A",
            "vote_average": None,
            "original_language": "N/A",
            "genres": [],
            "tmdb_id": None # Initialize tmdb_id
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
                    
                    release_date = data.get("release_date", "")
                    movie_data["year"] = release_date[:4] if release_date else "N/A"
                    
                    movie_data["release_date"] = release_date
                    movie_data["vote_average"] = data.get("vote_average")
                    movie_data["original_language"] = data.get("original_language", "N/A")
                    
                    genres_names = []
                    for genre_id in data.get("genre_ids", []):
                        if genre_id in TMDb_Genre_Map:
                            genres_names.append(TMDb_Genre_Map[genre_id])
                    movie_data["genres"] = genres_names
                    
                    movie_data["tmdb_id"] = data.get("id")
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
            return redirect(url_for('admin'))

    # Fetch all movies for displaying in the admin panel
    all_movies = list(movies.find().sort('_id', -1))
    for movie in all_movies:
        movie['_id'] = str(movie['_id']) # Convert ObjectId to string for template
    return render_template_string(admin_html, movies=all_movies)


@app.route('/delete_movie/<movie_id>')
def delete_movie(movie_id):
    try:
        # Delete the movie from MongoDB using its ObjectId
        result = movies.delete_one({"_id": ObjectId(movie_id)})
        if result.deleted_count == 1:
            print(f"Movie with ID {movie_id} deleted successfully!")
        else:
            print(f"Movie with ID {movie_id} not found.")
    except Exception as e:
        print(f"Error deleting movie with ID {movie_id}: {e}")
    
    return redirect(url_for('admin')) # Redirect back to the admin page


# New routes for navigation bar
@app.route('/movies_only')
def movies_only():
    # Only fetches items marked as 'movie' type
    movie_list = list(movies.find({"type": "movie"}).sort('_id', -1).limit(30))
    for movie in movie_list:
        movie['_id'] = str(movie['_id'])
    return render_template_string(index_html, movies=movie_list, query="")

@app.route('/webseries')
def webseries():
    # Only fetches items marked as 'series' type
    series_list = list(movies.find({"type": "series"}).sort('_id', -1).limit(30))
    for series in series_list:
        series['_id'] = str(series['_id'])
    return render_template_string(index_html, movies=series_list, query="")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

