"""
Combined Recipe App: User Input → Gemini (ingredient parsing) → Spoonacular (recipe search)
This Flask server accepts user dietary/health goals and food preferences,
processes them through Google Gemini to extract ingredients,
then queries Spoonacular API for recipes.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
import requests
import os

app = Flask(__name__)
CORS(app)

# API Keys (ideally use environment variables in production)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyDFS7kQUM3hmxjmWjQjwdbGbcauvjeOqFI")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "fe280e4084654ebda23631906f63fe87")

# Initialize Gemini client
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)

# Spoonacular API base URL
SPOONACULAR_BASE_URL = "https://api.spoonacular.com/recipes/findByIngredients"


def parse_ingredients_with_gemini(user_input):
    """
    Send user dietary/health goals and food preferences to Gemini.
    Request Gemini to extract and format as comma-separated ingredient list.
    
    Args:
        user_input (str): User's diet goals, health objectives, and food preferences
        
    Returns:
        str: Comma-separated list of ingredients (e.g., "tomato,cheese,basil")
    """
    try:
        # Create a chat session with Gemini
        chat = gemini_client.chats.create(model="gemini-2.0-flash")
        
        # Craft a specific prompt for ingredient extraction
        prompt = f"""You are a recipe ingredient extractor. The user has provided the following dietary/health goals and food preferences:

"{user_input}"

Based on this input, extract and return ONLY a comma-separated list of ingredients that would be suitable for recipes matching these goals and preferences. 

IMPORTANT: Return ONLY the comma-separated ingredient list, nothing else. Example format: "chicken,broccoli,garlic,olive oil"

Do not include explanations, bullet points, or any other text. Just the ingredients separated by commas."""
        
        response = chat.send_message(prompt)
        ingredients_str = response.text.strip()
        
        return ingredients_str
        
    except Exception as e:
        raise ValueError(f"Gemini API error: {str(e)}")


def fetch_recipes_from_spoonacular(ingredients):
    """
    Query Spoonacular API for recipes based on parsed ingredients.
    
    Args:
        ingredients (str): Comma-separated ingredient list
        
    Returns:
        list: List of recipe objects with id, title, image, and ingredient info
    """
    try:
        params = {
            "ingredients": ingredients,
            "number": 4,           # Number of recipes to return
            "ranking": 1,           # Prioritize recipes using most of the ingredients
            "apiKey": SPOONACULAR_API_KEY
        }
        
        response = requests.get(SPOONACULAR_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        recipes = []
        for recipe in data:
            recipes.append({
                "id": recipe.get("id"),
                "title": recipe.get("title"),
                "image": recipe.get("image"),
                "used_ingredients": [i["name"] for i in recipe.get("usedIngredients", [])],
                "missed_ingredients": [i["name"] for i in recipe.get("missedIngredients", [])],
            })
        
        return recipes
        
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Spoonacular API error: {str(e)}")


@app.route("/api/recipes", methods=["POST"])
def get_recipes_from_goals():
    """
    Main endpoint: Accept user dietary goals, parse with Gemini, fetch recipes from Spoonacular.
    
    Expected JSON payload:
    {
        "diet_goals": "I want to lose weight and eat healthy",
        "food_preferences": "I like Mediterranean cuisine, no meat on Mondays"
    }
    
    Or simpler:
    {
        "user_input": "Vegetarian, high protein, gluten-free"
    }
    
    Returns:
    {
        "success": true,
        "user_input": "...",
        "parsed_ingredients": "chicken,broccoli,...",
        "recipes": [...]
    }
    """
    try:
        data = request.get_json()
        
        # Accept both formats: combined "user_input" or separate fields
        if "user_input" in data:
            user_input = data.get("user_input", "").strip()
        else:
            diet_goals = data.get("diet_goals", "").strip()
            food_preferences = data.get("food_preferences", "").strip()
            user_input = f"Diet goals: {diet_goals}. Food preferences: {food_preferences}"
        
        if not user_input:
            return jsonify({"error": "Please provide either 'user_input' or both 'diet_goals' and 'food_preferences'"}), 400
        
        # Step 1: Parse user input with Gemini to extract ingredients
        parsed_ingredients = parse_ingredients_with_gemini(user_input)
        
        if not parsed_ingredients or parsed_ingredients.lower() == "none":
            return jsonify({
                "error": "Gemini could not extract ingredients from the provided input. Please try a more descriptive query.",
                "user_input": user_input
            }), 400
        
        # Step 2: Fetch recipes from Spoonacular using parsed ingredients
        recipes = fetch_recipes_from_spoonacular(parsed_ingredients)
        
        return jsonify({
            "success": True,
            "user_input": user_input,
            "parsed_ingredients": parsed_ingredients,
            "recipe_count": len(recipes),
            "recipes": recipes
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify server is running."""
    return jsonify({"status": "ok", "message": "Recipe API is running"}), 200


if __name__ == "__main__":
    print("Starting Combined Recipe App...")
    print("Gemini API Key:", "configured" if GOOGLE_API_KEY else "NOT SET")
    print("Spoonacular API Key:", "configured" if SPOONACULAR_API_KEY else "NOT SET")
    app.run(debug=True, port=5001)
