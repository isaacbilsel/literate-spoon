
SPOONACULAR_API_KEY = "fe280e4084654ebda23631906f63fe87"
# app.py
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Get Spoonacular API key from environment variable
# SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

if not SPOONACULAR_API_KEY:
    raise ValueError("Missing Spoonacular API key. Set it as SPOONACULAR_API_KEY environment variable.")

BASE_URL = "https://api.spoonacular.com/recipes/findByIngredients"


@app.route("/recipes", methods=["GET"])
def get_recipes():
    # Expect ?ingredients=tomato,cheese,basil
    ingredients = request.args.get("ingredients")
    if not ingredients:
        return jsonify({"error": "Please provide ingredients as a comma-separated list."}), 400

    try:
        params = {
            "ingredients": ingredients,
            "number": 5,       # how many recipes to return
            "ranking": 1,      # prioritize recipes using most of your ingredients
            "apiKey": SPOONACULAR_API_KEY
        }

        response = requests.get(BASE_URL, params=params)
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

        return jsonify({"recipes": recipes})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
    # In browser test example:
    # http://127.0.0.1:5000/recipes?ingredients=tomato,cheese,basil
