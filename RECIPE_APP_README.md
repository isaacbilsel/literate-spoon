# Combined Recipe App: Gemini → Spoonacular Pipeline

A Flask-based recipe recommendation system that combines **Google Gemini AI** and **Spoonacular API**.

## Workflow

1. **User Input**: Accepts dietary goals and food preferences
2. **Gemini Processing**: Converts natural language input into a structured ingredient list
3. **Spoonacular Query**: Fetches recipes matching the extracted ingredients
4. **Output**: Returns recipes with details (title, image, used/missed ingredients)

## File Structure

```
proj_test/
├── combined_recipe_app.py          # NEW: Main Flask app (Gemini + Spoonacular)
├── google_api.py                   # Original: Gemini standalone example
├── spoonacular.py                  # Original: Spoonacular standalone example
├── server.py                        # Original: Basic login server
├── json_test.js                     # Original: React login form
└── README.md                        # This file
```

## Prerequisites

- Python 3.8+
- pip

## Installation

1. Install required packages:
```bash
python3 -m pip install --user Flask flask_cors google-genai requests
```

2. Set API Keys (optional - defaults are embedded in the file):
```bash
export GOOGLE_API_KEY="your_google_api_key_here"
export SPOONACULAR_API_KEY="your_spoonacular_api_key_here"
```

If not set, the app will use the hardcoded keys from `combined_recipe_app.py`.

## Running the Server

Start the Flask server:
```bash
cd "/Users/isaacbilsel/Library/Mobile Documents/com~apple~CloudDocs/Documents/GW_Classes/csci6221/proj_test"
python3 combined_recipe_app.py
```

Expected output:
```
Starting Combined Recipe App...
Gemini API Key: configured
Spoonacular API Key: configured
 * Running on http://127.0.0.1:5001
 * Debug mode: on
```

## API Endpoints

### 1. POST `/api/recipes` - Get Recipes from User Input

This is the main endpoint. You send your dietary goals/preferences, and get back recipes.

**Two ways to send your request:**

**Option A (Simpler):** Send combined input
```json
{
  "user_input": "vegetarian high protein Mediterranean"
}
```

**Option B (More detailed):** Send separate fields
```json
{
  "diet_goals": "lose weight and build muscle",
  "food_preferences": "Asian cuisine, no red meat"
}
```

**What you get back:**
```json
{
  "success": true,
  "user_input": "vegetarian high protein Mediterranean",
  "parsed_ingredients": "chickpeas,tofu,spinach,tomatoes,olive oil",
  "recipe_count": 10,
  "recipes": [
    {
      "id": 595736,
      "title": "Mediterranean Chickpea Salad",
      "image": "https://spoonacular.com/recipeImages/595736-356x236.jpg",
      "used_ingredients": ["chickpeas", "spinach", "tomatoes"],
      "missed_ingredients": ["feta cheese", "olive oil"]
    },
    {
      "id": 716627,
      "title": "Tofu Buddha Bowl",
      "image": "https://spoonacular.com/recipeImages/716627-356x236.jpg",
      "used_ingredients": ["tofu", "spinach"],
      "missed_ingredients": ["tahini", "lemon"]
    }
  ]
}
```

### 2. GET `/health` - Health Check

Simple endpoint to verify the server is running. No input needed.

**What you get back:**
```json
{
  "status": "ok",
  "message": "Recipe API is running"
}
```

## Testing with curl (Copy-Paste These Commands)

**See the detailed testing guide in `TESTING_GUIDE.md` for step-by-step instructions with expected outputs.**

Quick examples:

**Test 1: Health check (verify server is running)**
```bash
curl http://localhost:5001/health
```

**Test 2: Get recipes (simple input)**
```bash
curl -X POST http://localhost:5001/api/recipes \
  -H "Content-Type: application/json" \
  -d '{"user_input":"vegetarian high protein Mediterranean"}'
```

**Test 3: Get recipes (structured input)**
```bash
curl -X POST http://localhost:5001/api/recipes \
  -H "Content-Type: application/json" \
  -d '{"diet_goals":"lose weight","food_preferences":"Asian cuisine, vegetarian"}'
```

## Integration with React Frontend

To integrate with a React app, update your fetch call:

```javascript
const response = await fetch("http://localhost:5001/api/recipes", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    user_input: userGoalsAndPreferences
  }),
});

const data = await response.json();
if (data.success) {
  setRecipes(data.recipes);
  setParsedIngredients(data.parsed_ingredients);
}
```

## How It Works (Step-by-Step)

1. **User submits input** → POST `/api/recipes` with dietary goals/preferences
2. **Gemini processes** → Sends prompt: "Extract ingredients from this description in comma-separated format"
3. **Gemini returns** → Comma-separated ingredient list (e.g., "tomato,basil,mozzarella")
4. **Spoonacular query** → Uses ingredients to find matching recipes
5. **Results returned** → JSON with recipe details, images, and used/missed ingredients

## Error Handling

- **Missing input**: Returns 400 error if neither `user_input` nor `diet_goals`/`food_preferences` provided
- **Gemini failure**: Returns 500 error with Gemini API error details
- **Spoonacular failure**: Returns 500 error with Spoonacular API error details
- **Invalid extraction**: Returns 400 if Gemini cannot extract meaningful ingredients

## Example Responses

### Success Case:
```json
{
  "success": true,
  "user_input": "Vegan, high protein",
  "parsed_ingredients": "lentils,tofu,quinoa,spinach",
  "recipe_count": 10,
  "recipes": [ ... ]
}
```

### Error Case:
```json
{
  "error": "Gemini API error: Invalid API key"
}
```

## Production Recommendations

1. **Environment variables**: Move API keys to `.env` file instead of hardcoding
   ```python
   from dotenv import load_dotenv
   GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
   ```

2. **Rate limiting**: Add request throttling to prevent abuse

3. **Caching**: Cache Gemini results for repeated inputs to reduce costs

4. **Validation**: Add stricter input validation for user input length/content

5. **Logging**: Add structured logging for debugging and monitoring

6. **CORS whitelist**: Restrict CORS to your frontend domain instead of allowing all origins

## Original Files (Unchanged)

- `google_api.py`: Standalone Gemini chat example
- `spoonacular.py`: Standalone Spoonacular recipe API example
- `server.py`: Basic Flask login server on port 5000
- `json_test.js`: React login form component

## Troubleshooting

**Issue**: "Connection refused" on localhost:5001
- Ensure Flask server is running (you should see startup messages in your terminal)
- See `TESTING_GUIDE.md` for step-by-step instructions

**Issue**: "Invalid API key"
- Check that GOOGLE_API_KEY and SPOONACULAR_API_KEY are correctly set
- By default, the app uses embedded keys from the file

**Issue**: Gemini returns empty or "None"
- Try rephrasing the user input with more specific diet/food keywords
- Example: instead of "food", try "vegetarian Mediterranean dishes"

**Issue**: Port 5000 conflict (from earlier session)
- The combined app runs on port 5001 (not 5000) to avoid conflicts with system services

**For detailed testing steps with expected outputs, see `TESTING_GUIDE.md`** ← Start here!

## License

Educational project for CSCI 6221
