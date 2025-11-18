"""
Production-ready Flask application for the recipe recommendation system.
Main entry point for deployment on Render/Railway.
"""

import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from app_models import UserInput, ValidationError, APIError, ExternalAPIError
from app_services import GeminiService, SpoonacularService, RecipeService

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# CORS configuration - configure for production
NETLIFY_DOMAIN = os.getenv("NETLIFY_DOMAIN", "localhost:3000")
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5001",
    f"https://{NETLIFY_DOMAIN}",
]

cors_config = {
    "origins": ALLOWED_ORIGINS,
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type"],
    "max_age": 3600
}
CORS(app, resources={r"/api/*": cors_config})

# Initialize services
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

if not GOOGLE_API_KEY or not SPOONACULAR_API_KEY:
    logger.warning("Missing API keys - app may not function correctly")

gemini_service = GeminiService(GOOGLE_API_KEY)
spoonacular_service = SpoonacularService(SPOONACULAR_API_KEY)
recipe_service = RecipeService(gemini_service, spoonacular_service)

# Track start time for uptime
start_time = datetime.now()


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for deployment monitoring."""
    uptime_seconds = (datetime.now() - start_time).total_seconds()
    return jsonify({
        "status": "ok",
        "uptime_seconds": int(uptime_seconds),
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/api/recipes", methods=["POST"])
def get_recipes():
    """
    Main endpoint: Accept user data and return personalized recipes.
    
    Request JSON:
    {
        "height_cm": 180,
        "weight_kg": 75,
        "allergies": ["peanuts", "shellfish"],
        "food_preferences": "Mediterranean, vegetarian",
        "diet_goals": "lose weight, high protein"
    }
    
    Response (success):
    {
        "success": true,
        "user_metrics": {...},
        "parsed_ingredients": "...",
        "recipe_count": 4,
        "recipes": [...]
    }
    """
    try:
        # Parse and validate request JSON
        data = request.get_json()
        if not data:
            logger.warning("Empty request body")
            return jsonify({
                "success": False,
                "error": "Request body must be JSON"
            }), 400
        
        logger.info(f"Processing recipe request - height: {data.get('height_cm')}, weight: {data.get('weight_kg')}")
        
        # Validate user input
        try:
            user_input = UserInput.from_dict(data)
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}")
            return jsonify({
                "success": False,
                "error": e.message,
                "field": e.field
            }), 400
        
        # Get recipes
        try:
            parsed_ingredients, recipes, metrics = recipe_service.get_recipes_for_user(user_input)
        except ExternalAPIError as e:
            logger.error(f"External API error: {e.message}")
            return jsonify({
                "success": False,
                "error": e.message,
                "type": "external_api_error"
            }), 500
        
        # Build response
        response = {
            "success": True,
            "user_metrics": metrics.to_dict(),
            "parsed_ingredients": parsed_ingredients,
            "recipe_count": len(recipes),
            "recipes": [r.to_dict() for r in recipes]
        }
        
        logger.info(f"Successfully returned {len(recipes)} recipes")
        return jsonify(response), 200
        
    except Exception as e:
        logger.exception(f"Unexpected error in /api/recipes: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "type": "internal_error"
        }), 500


@app.route("/api/recipes", methods=["OPTIONS"])
def handle_preflight():
    """Handle CORS preflight requests."""
    return "", 200


@app.errorhandler(400)
def handle_bad_request(e):
    """Handle 400 errors."""
    logger.warning(f"Bad request: {str(e)}")
    return jsonify({
        "success": False,
        "error": "Bad request"
    }), 400


@app.errorhandler(404)
def handle_not_found(e):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def handle_server_error(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {str(e)}")
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("FLASK_ENV", "production") == "development"
    
    logger.info(f"Starting Flask app on port {port} (debug={debug})")
    logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")
    logger.info(f"Gemini API: {'configured' if GOOGLE_API_KEY else 'NOT SET'}")
    logger.info(f"Spoonacular API: {'configured' if SPOONACULAR_API_KEY else 'NOT SET'}")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
