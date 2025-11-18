## Project Backend Summary

This document describes the current state of the Python backend (what is implemented now).

**Framework & Structure**
- **Framework**: Flask (app created via `Flask()` in `main.py`).
- **Main entry point**: `main.py` (runs `app.run()` when executed).
- **Key files**: `main.py`, `app_models.py`, `app_services.py`, `test_backend.py`, `requirements.txt`, `README.md`, `api/recipes.json`.

**Current API Endpoints**
- **GET `/health`**: Health check; returns `{status, uptime_seconds, timestamp}`.
- **POST `/api/recipes`**: Main endpoint; accepts JSON with `height_cm`, `weight_kg`, `allergies`, `food_preferences`, `diet_goals`. Validates input, calculates user metrics, uses Gemini to extract ingredients, queries Spoonacular, enriches and filters recipes, and returns recipes + metrics.
- **OPTIONS `/api/recipes`**: CORS preflight handler.
- **Error handlers**: JSON handlers for 400, 404, 500 defined in `main.py`.

**External Integrations**
- **Google Gemini**: Integrated via `google.genai` in `app_services.GeminiService`. Used to parse/extract a comma-separated ingredient list from user preferences/goals while excluding allergens. Calls: chat creation and `send_message(prompt)`; errors wrapped as `ExternalAPIError`.
- **Spoonacular API**: Integrated via `requests` in `app_services.SpoonacularService`. Used endpoints: `/recipes/findByIngredients`, `/recipes/{id}/information` (nutrition), `/recipes/{id}/priceBreakdown` (pricing). Simple in-memory cache (`_recipe_cache`) stores recipe details per process.
- **Other**: Environment variables used: `GOOGLE_API_KEY`, `SPOONACULAR_API_KEY`, `NETLIFY_DOMAIN`. No other external services in code.

**Data Handling**
- **Models (in `app_models.py`)**:
  - `UserInput` — validation and normalization (`from_dict`).
  - `UserMetrics` — BMI, TDEE, macro targets, `to_dict()`.
  - `RecipeNutrition`, `RecipePricing`, `Recipe` — parse/hold recipe details, `to_dict()` and macro alignment scoring.
  - Exceptions: `ValidationError`, `APIError`, `ExternalAPIError`.
- **Storage / State**: No persistent database. All data is processed in-memory. Spoonacular recipe details cached in-memory per process (`SpoonacularService._recipe_cache`). `api/recipes.json` exists but is unused by runtime code.
- **Request / Response schemas**: `/api/recipes` request expects `height_cm` (int 100–250), `weight_kg` (int 30–300), `allergies` (array, max 10), `food_preferences` (1–500 chars), `diet_goals` (1–500 chars). Successful response contains `success`, `user_metrics`, `parsed_ingredients`, `recipe_count`, and `recipes` (each recipe matches `Recipe.to_dict()` format).

**Dependencies**
- From `requirements.txt`:
  - `Flask==3.0.3`
  - `flask-cors==4.0.0`
  - `python-dotenv==1.0.1`
  - `google-genai==1.10.0` (Gemini client)
  - `requests==2.32.2`
  - `gunicorn==21.2.0`
- **Python version**: Not explicitly pinned; README uses `python3`. Use a modern Python 3.x (3.8+) for compatibility with listed packages.

**Missing Pieces / Next Steps to Add Persistence**
- **Database integration**: None currently. No ORM or DB connection code present.
- **To add persistence**: choose a DB (SQLite/Postgres), add an ORM (e.g., SQLAlchemy), add connection config via env vars, create models and migration scripts, and persist desired data (cached recipes, request logs, users). Move per-process caches to persistent store if cross-process sharing is required.

---
Document created from current repository sources: `main.py`, `app_services.py`, `app_models.py`, `test_backend.py`, `requirements.txt`, and `README.md`.
