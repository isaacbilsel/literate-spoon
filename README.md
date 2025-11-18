# Literate Spoon Backend

**CSCI 6221 Course Project**

A comprehensive Flask-based REST API for personalized recipe recommendations and meal planning. Combines **Google Gemini AI** and **Spoonacular API** with user authentication, profile management, meal planning, and chat functionality.

## Quick Start (5 minutes)

### 1. Setup Local Environment

```bash
cd literate-spoon

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your API keys (see below)
```

### 2. Get API Keys

- **Google Gemini**: https://ai.google.dev/ (free tier, 60 requests/minute)
- **Spoonacular**: https://spoonacular.com/food-api (free tier, 150 requests/day)

Add them to your `.env` file:
```
FLASK_ENV=development
PORT=5001
SECRET_KEY=dev_secret_key_change_in_production
GOOGLE_API_KEY=your_key_here
SPOONACULAR_API_KEY=your_key_here
NETLIFY_DOMAIN=localhost:3000
```

### 3. Initialize Database

```bash
python3 -c "from app_models import init_db; init_db(); print('Database initialized')"
```

### 4. Run the Server

```bash
python3 main.py
```

You should see:
```
Starting Flask app on port 5001 (debug=True)
Gemini API: configured
Spoonacular API: configured
CORS allowed origins: ['http://localhost:3000', 'http://localhost:5001', 'https://localhost:3000']
```

### 5. Test It Works

```bash
curl http://localhost:5001/health
```

Expected response:
```json
{
  "status": "ok",
  "uptime_seconds": 2,
  "timestamp": "2025-11-18T12:00:00.000000"
}
```

---

## Complete API Reference

All endpoints return JSON. Protected endpoints require `Authorization: Bearer {token}` header.

### Authentication Endpoints

#### POST `/api/auth/register`
Register new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "firstName": "John",
  "gender": "M",
  "zipCode": "90210"
}
```

**Response (201):**
```json
{
  "user": {"id": 1, "email": "user@example.com"},
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshTokenSetCookie": false
}
```

---

#### POST `/api/auth/login`
Authenticate user and get token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response (200):**
```json
{
  "user": {"id": 1, "email": "user@example.com"},
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshTokenSetCookie": false
}
```

---

#### GET `/api/auth/me`
Get current user info (requires auth).

**Response (200):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "user",
    "created_at": "2025-11-18T10:00:00"
  },
  "profile": {
    "id": 1,
    "userId": 1,
    "firstName": "John",
    "gender": "M",
    "zipCode": "90210"
  }
}
```

---

#### POST `/api/auth/logout`
Logout (JWT stateless, mainly for frontend).

**Response (200):**
```json
{"message": "Logged out successfully"}
```

---

#### POST `/api/auth/refresh`
Refresh access token (requires auth).

**Response (200):**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshTokenSetCookie": false
}
```

---

### Profile Endpoints

#### GET `/api/profile`
Get user profile (requires auth).

**Response (200):**
```json
{
  "id": 1,
  "userId": 1,
  "firstName": "John",
  "gender": "M",
  "zipCode": "90210",
  "bio": "Fitness enthusiast",
  "createdAt": "2025-11-18T10:00:00"
}
```

---

#### PUT/PATCH `/api/profile`
Update user profile (requires auth).

**Request:**
```json
{
  "firstName": "John",
  "gender": "M",
  "zipCode": "90210",
  "bio": "Updated bio"
}
```

**Response (200):**
```json
{
  "message": "Profile updated successfully",
  "profile": {...}
}
```

---

### Meal Plan Endpoints

#### GET `/api/meal-plans`
List meal plans (requires auth).

**Response (200):**
```json
{
  "meal_plans": [
    {
      "id": 1,
      "userId": 1,
      "name": "Weekly Plan",
      "description": "Healthy meals",
      "isActive": true,
      "createdAt": "2025-11-18T10:00:00"
    }
  ]
}
```

---

#### POST `/api/meal-plans`
Create meal plan (requires auth).

**Request:**
```json
{
  "name": "Weekly Plan",
  "description": "Healthy meals",
  "meals": "[]"
}
```

**Response (201):**
```json
{
  "message": "Meal plan created",
  "meal_plan": {...}
}
```

---

#### GET `/api/meal-plans/{id}`
Get specific meal plan (requires auth).

**Response (200):**
```json
{
  "id": 1,
  "name": "Weekly Plan",
  "isActive": true
}
```

---

#### PUT/PATCH `/api/meal-plans/{id}`
Update meal plan (requires auth).

**Request:**
```json
{
  "name": "Updated Plan",
  "meals": "[\"Mon\", \"Tue\"]"
}
```

**Response (200):**
```json
{
  "message": "Meal plan updated",
  "meal_plan": {...}
}
```

---

#### POST `/api/meal-plans/{id}/activate`
Activate meal plan (requires auth).

**Response (200):**
```json
{
  "message": "Meal plan activated",
  "meal_plan": {"id": 1, "isActive": true}
}
```

---

#### GET `/api/meal-plans/{id}/grocery-list`
Get grocery list for meal plan (requires auth).

**Response (200):**
```json
{
  "id": 1,
  "userId": 1,
  "mealPlanId": 1,
  "items": "[\"milk\", \"eggs\"]"
}
```

---

### Grocery List Endpoints

#### GET `/api/grocery-lists`
List grocery lists (requires auth).

**Response (200):**
```json
{
  "grocery_lists": [
    {
      "id": 1,
      "userId": 1,
      "items": "[\"milk\", \"eggs\"]"
    }
  ]
}
```

---

#### POST `/api/grocery-lists`
Create grocery list (requires auth).

**Request:**
```json
{
  "items": "[\"milk\", \"eggs\", \"bread\"]"
}
```

**Response (201):**
```json
{
  "message": "Grocery list created",
  "grocery_list": {...}
}
```

---

#### GET `/api/grocery-lists/{id}`
Get specific grocery list (requires auth).

**Response (200):**
```json
{
  "id": 1,
  "items": "[\"milk\", \"eggs\"]"
}
```

---

#### PUT/PATCH `/api/grocery-lists/{id}`
Update grocery list (requires auth).

**Request:**
```json
{
  "items": "[\"milk\", \"eggs\", \"cheese\"]"
}
```

**Response (200):**
```json
{
  "message": "Grocery list updated",
  "grocery_list": {...}
}
```

---

### Chat Endpoints

#### POST `/api/chat/parse`
Parse chat message (requires auth).

**Request:**
```json
{
  "message": "I want vegetarian meals for weight loss"
}
```

**Response (200):**
```json
{
  "message": "I want vegetarian meals for weight loss",
  "response": "I received your message: '...' How can I help?",
  "chat_id": 1
}
```

---

#### GET `/api/chat/history`
Get chat history (requires auth).

**Response (200):**
```json
{
  "chat_history": [
    {
      "id": 1,
      "userId": 1,
      "message": "...",
      "response": "...",
      "createdAt": "2025-11-18T10:00:00"
    }
  ]
}
```

---

### Recipe Endpoint

#### POST `/api/recipes`
Get personalized recipes (no auth required).

**Request:**
```json
{
  "height_cm": 180,
  "weight_kg": 75,
  "allergies": ["peanuts"],
  "food_preferences": "Mediterranean",
  "diet_goals": "weight loss"
}
```

**Response (200):**
```json
{
  "success": true,
  "user_metrics": {
    "height_cm": 180,
    "weight_kg": 75,
    "bmi": 23.1,
    "tdee_estimate": 2805,
    "macro_targets": {
      "protein_g": 210,
      "carbs_g": 280,
      "fats_g": 93
    }
  },
  "recipe_count": 4,
  "recipes": [...]
}
```

---

### Utility Endpoints

#### GET `/health`
Health check (no auth required).

**Response (200):**
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "timestamp": "2025-11-18T10:00:00"
}
```

---

## Testing

### Run All Tests

```bash
python -m pytest test_endpoints_simple.py -v
```

Output:
```
test_register_success PASSED              [  3%]
test_login_success PASSED                 [ 10%]
test_get_profile PASSED                   [ 14%]
test_create_meal_plan PASSED              [ 50%]
test_parse_chat PASSED                    [ 78%]
...
28 passed in 2.33s ✓
```

### Manual Testing

```bash
# Register
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"pass123","firstName":"Test"}'

# Login (save token)
TOKEN=$(curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"pass123"}' | jq -r '.accessToken')

# Get profile
curl -H "Authorization: Bearer $TOKEN" http://localhost:5001/api/profile

# Create meal plan
curl -X POST http://localhost:5001/api/meal-plans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Weekly Plan"}'
```

---

## Database

SQLite database with SQLAlchemy ORM.

**Models:**
- **User**: Email, password hash, role, timestamps
- **Profile**: Bio, preferences, linked to User
- **MealPlan**: Meals list, active status
- **GroceryList**: Shopping items, linked to MealPlan
- **ChatMessage**: Message + response, linked to User

**Initialize:**
```bash
python3 -c "from app_models import init_db; init_db()"
```

**Reset:**
```bash
rm literate_spoon.db && python3 -c "from app_models import init_db; init_db()"
```

---

## Authentication

All protected endpoints require JWT token in header:

```bash
Authorization: Bearer {accessToken}
```

**Token Details:**
- Valid for 15 minutes
- Contains user_id and role
- Use `/api/auth/refresh` to get new token
- Use `/api/auth/logout` to invalidate (frontend only, JWT stateless)

---

## Error Responses

Standard error format:

```json
{
  "error": "Error message",
  "field": "field_name (optional)"
}
```

**Common Codes:**
- **200**: Success
- **201**: Created
- **400**: Bad request
- **401**: Unauthorized
- **404**: Not found
- **409**: Conflict
- **500**: Server error

---

## Architecture

```
Frontend (React, localhost:3000)
    ↓ (CORS-enabled)
Flask API (main.py, port 5001)
    ↓
Route Handlers (auth, profile, meal-plans, grocery, chat, recipes)
    ↓
Business Logic (app_services.py)
    ↓
SQLAlchemy ORM
    ↓
SQLite Database (literate_spoon.db)
    ↓
External APIs (Gemini, Spoonacular)
```

---

## Project Structure

```
literate-spoon/
├── main.py                    # Flask app & endpoints
├── app_models.py              # Database models & validation
├── app_services.py            # Business logic (AI, recipes)
├── test_endpoints_simple.py   # Test suite (28 tests)
├── requirements.txt           # Dependencies
├── .env                       # Environment config
├── .gitignore                 # Git ignore
├── README.md                  # This file
└── literate_spoon.db          # SQLite database
```

---

## Performance

- **Auth endpoints**: ~50-100ms
- **Profile/Meal Plan/Grocery**: ~20-50ms
- **Chat parse**: ~50-100ms
- **Recipe search**: 8-15s (external APIs)
- **Health check**: ~10ms

---

## Development

### Install Dependencies

```bash
pip install -r requirements.txt
pip install pytest pytest-flask  # for testing
```

### Run Tests

```bash
python -m pytest test_endpoints_simple.py -v
```

### Code Quality

- All endpoints validated server-side
- Passwords hashed with bcrypt
- JWTs with 15-minute expiry
- CORS configured for frontend
- Database auto-created

---

## Deployment

### Development
```bash
python3 main.py
```

### Production
```bash
gunicorn -w 4 -b 0.0.0.0:5001 main:app
```

**Required env vars:**
- `FLASK_ENV=production`
- `SECRET_KEY=<strong-random-key>`
- `GOOGLE_API_KEY=<key>`
- `SPOONACULAR_API_KEY=<key>`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Start server: `python3 main.py` |
| 401 Unauthorized | Include valid token in header |
| API key error | Check `.env` has valid keys |
| CORS error | Update `NETLIFY_DOMAIN` in `.env` |
| Database locked | Reset: `rm literate_spoon.db && python3 -c "from app_models import init_db; init_db()"` |

---

## Support

For issues:
1. Run tests: `python -m pytest test_endpoints_simple.py -v`
2. Check logs in terminal where you ran `python3 main.py`
3. Verify `.env` file has all required keys
4. Check API quotas at Gemini and Spoonacular websites

---

## License

Educational project for CSCI 6221 - George Washington University

### POST `/api/recipes` - Get Personalized Recipes

Accepts user health metrics and preferences, returns recipes with nutritional info and pricing.

**Request:**
```json
{
  "height_cm": 180,
  "weight_kg": 75,
  "allergies": ["peanuts", "shellfish"],
  "food_preferences": "Mediterranean, high protein, vegetarian options",
  "diet_goals": "lose weight, build muscle"
}
```

**Input Validation:**
| Field | Type | Valid Range | Example |
|-------|------|---|---|
| `height_cm` | integer | 100-250 cm | 180 |
| `weight_kg` | integer | 30-300 kg | 75 |
| `allergies` | array | 0-10 items | `["peanuts"]` |
| `food_preferences` | string | 1-500 chars | "Mediterranean" |
| `diet_goals` | string | 1-500 chars | "lose weight" |

**Success Response (200):**
```json
{
  "success": true,
  "user_metrics": {
    "height_cm": 180,
    "weight_kg": 75,
    "bmi": 23.1,
    "tdee_estimate": 2805,
    "macro_targets": {
      "protein_g": 210,
      "carbs_g": 280,
      "fats_g": 93
    }
  },
  "parsed_ingredients": "chicken,broccoli,brown rice,olive oil",
  "recipe_count": 4,
  "recipes": [
    {
      "id": 595736,
      "title": "Grilled Chicken with Broccoli",
      "image": "https://spoonacular.com/...",
      "used_ingredients": ["chicken", "broccoli"],
      "missed_ingredients": ["olive oil"],
      "macronutrients": {
        "calories": 450,
        "protein_g": 55,
        "carbs_g": 25,
        "fats_g": 15
      },
      "pricing": {
        "cost_per_serving": 3.50,
        "currency": "USD",
        "servings": 2
      },
      "macro_alignment_score": 92
    }
  ]
}
```

**Error Response (400 - Invalid Input):**
```json
{
  "success": false,
  "error": "Invalid height: must be between 100-250 cm",
  "field": "height_cm"
}
```

**Error Response (500 - API Error):**
```json
{
  "success": false,
  "error": "Gemini API error: rate limit exceeded",
  "type": "external_api_error"
}
```

### GET `/health` - Health Check

Simple endpoint to verify the server is running.

**Response:**
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "timestamp": "2025-11-17T12:00:00.000000"
}
```

---

## Architecture & How It Works

### Data Flow

```
User Input (height, weight, allergies, preferences, goals)
    ↓
Input Validation (type-safe, range-checked)
    ↓
User Metrics Calculation (BMI, TDEE, macro targets)
    ↓
Gemini Processing (extract ingredients, exclude allergies)
    ↓
Spoonacular Search (find recipes matching ingredients)
    ↓
Recipe Enrichment (fetch nutrition & pricing for each)
    ↓
Allergen Filtering (remove recipes with any allergens)
    ↓
Sorting (by macro alignment + cost per serving)
    ↓
Response (top 8 recipes with full details)
```

### Key Features

**1. Intelligent Input Validation**
- Type-safe integer validation for height/weight with range checks
- Array validation for allergies with size limit
- String fields with character limits
- Field-level error reporting for debugging

**2. Health Metrics Calculation**
- **BMI**: `weight_kg / (height_cm/100)²`
- **TDEE (Total Daily Energy Expenditure)**: Uses Mifflin-St Jeor equation with 1.5x activity factor
- **Macro Targets**: Dynamic based on diet goal
  - Weight Loss: 30% protein, 40% carbs, 30% fats
  - Muscle Gain: 35% protein, 45% carbs, 20% fats
  - General Health: 25% protein, 50% carbs, 25% fats

**3. Ingredient Extraction (Gemini)**
- Converts natural language diet goals/preferences into structured ingredient list
- Automatically excludes allergens from generated ingredients
- Handles ambiguous inputs gracefully

**4. Recipe Search & Enrichment (Spoonacular)**
- Searches for recipes matching extracted ingredients (15 results)
- Fetches full nutritional information for each
- Attempts to fetch pricing information (optional, doesn't fail if unavailable)
- Parses and normalizes all data

**5. Allergen Safety**
- All recipe ingredients checked against user allergy list
- Any matching allergen = recipe filtered out
- Conservative approach: if in doubt, exclude

**6. Smart Sorting**
- Primary: Macro alignment score (0-100, how well recipe matches user targets)
- Secondary: Cost per serving (lower is better)
- Returns top 8 recipes

### File Structure

```
literate-spoon/
├── main.py                    # Flask app entry point
├── app_models.py              # Data models & validation
├── app_services.py            # Business logic (Gemini, Spoonacular, Recipe)
├── test_backend.py            # Automated test suite
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template (copy to .env)
├── README.md                  # This file
└── api/
    └── recipes.json           # Local data storage (if needed)
```

---

## Testing

### Run Automated Tests

```bash
python3 test_backend.py
```

Expected output:
```
test_valid_user_input ... ok
test_invalid_height ... ok
test_invalid_weight ... ok
test_invalid_allergies ... ok
test_user_metrics_bmi ... ok
test_user_metrics_tdee ... ok
test_nutrition_parsing ... ok
test_pricing_parsing ... ok

ALL TESTS PASSED ✓
```

### Manual Testing with curl

**Test 1: Health Check**
```bash
curl http://localhost:5001/health
```

**Test 2: Simple Recipe Request**
```bash
curl -X POST http://localhost:5001/api/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "height_cm": 180,
    "weight_kg": 75,
    "allergies": [],
    "food_preferences": "Mediterranean",
    "diet_goals": "lose weight"
  }'
```

**Test 3: With Allergies**
```bash
curl -X POST http://localhost:5001/api/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "height_cm": 165,
    "weight_kg": 60,
    "allergies": ["peanuts", "shellfish", "dairy"],
    "food_preferences": "Asian, vegetarian",
    "diet_goals": "build muscle"
  }'
```

**Test 4: Invalid Input (should return 400)**
```bash
curl -X POST http://localhost:5001/api/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "height_cm": 50,
    "weight_kg": 75,
    "allergies": [],
    "food_preferences": "Mediterranean",
    "diet_goals": "lose weight"
  }'
```

---

## Frontend Integration

### React Example

```javascript
const BACKEND_URL = "http://localhost:5001";

async function getRecipes(userData) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/recipes`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        height_cm: parseInt(userData.height),
        weight_kg: parseInt(userData.weight),
        allergies: userData.allergies.split(",").map(a => a.trim()),
        food_preferences: userData.preferences,
        diet_goals: userData.goals
      })
    });

    const data = await response.json();
    
    if (data.success) {
      // Display user metrics
      console.log(`BMI: ${data.user_metrics.bmi}`);
      console.log(`Daily Calories: ${data.user_metrics.tdee_estimate}`);
      console.log(`Macro Targets: ${data.user_metrics.macro_targets.protein_g}g protein`);
      
      // Display recipes
      data.recipes.forEach(recipe => {
        console.log(`${recipe.title}`);
        console.log(`Macros: ${recipe.macronutrients.protein_g}g protein, ${recipe.macronutrients.carbs_g}g carbs`);
        console.log(`Cost: $${recipe.pricing.cost_per_serving}/serving`);
        console.log(`Alignment Score: ${recipe.macro_alignment_score}/100`);
      });
    } else {
      console.error(`Error: ${data.error}`);
    }
  } catch (error) {
    console.error("Network error:", error);
  }
}
```

### JavaScript/HTML Example

```html
<!DOCTYPE html>
<html>
<head>
  <title>Recipe Finder</title>
</head>
<body>
  <h1>Get Personalized Recipes</h1>
  
  <form id="recipeForm">
    <label>Height (cm): <input type="number" name="height_cm" required></label>
    <label>Weight (kg): <input type="number" name="weight_kg" required></label>
    <label>Allergies (comma-separated): <input type="text" name="allergies"></label>
    <label>Preferences: <input type="text" name="food_preferences" required></label>
    <label>Diet Goals: <input type="text" name="diet_goals" required></label>
    <button type="submit">Get Recipes</button>
  </form>

  <div id="results"></div>

  <script>
    document.getElementById("recipeForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const formData = new FormData(e.target);
      const data = {
        height_cm: parseInt(formData.get("height_cm")),
        weight_kg: parseInt(formData.get("weight_kg")),
        allergies: formData.get("allergies") ? formData.get("allergies").split(",").map(a => a.trim()) : [],
        food_preferences: formData.get("food_preferences"),
        diet_goals: formData.get("diet_goals")
      };

      const response = await fetch("http://localhost:5001/api/recipes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });

      const result = await response.json();
      
      if (result.success) {
        let html = `<h2>Recipes (${result.recipe_count})</h2>`;
        result.recipes.forEach(recipe => {
          html += `
            <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0;">
              <h3>${recipe.title}</h3>
              <img src="${recipe.image}" width="200">
              <p>Protein: ${recipe.macronutrients.protein_g}g | Cost: $${recipe.pricing.cost_per_serving}</p>
              <p>Alignment Score: ${recipe.macro_alignment_score}/100</p>
            </div>
          `;
        });
        document.getElementById("results").innerHTML = html;
      } else {
        document.getElementById("results").innerHTML = `<p style="color:red;">Error: ${result.error}</p>`;
      }
    });
  </script>
</body>
</html>
```

---

## Error Handling & Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid height: must be between 100-250 cm" | Height out of range | Use height between 100-250 cm |
| "allergies must be an array" | Wrong data type | Send allergies as array: `["peanuts"]` |
| "Gemini API error: Invalid API key" | API key incorrect or expired | Check `GOOGLE_API_KEY` in `.env` |
| "Spoonacular search failed" | API key invalid or rate limit exceeded | Check `SPOONACULAR_API_KEY`, wait if rate limited |
| "No recipes returned" | Allergies too restrictive | Try with fewer allergies |
| CORS error from frontend | Domain not in whitelist | Update `NETLIFY_DOMAIN` in `.env` to match your frontend domain |
| "Connection refused" | Server not running | Run `python3 main.py` in another terminal |

### Debugging Tips

**1. Check Server is Running**
```bash
curl http://localhost:5001/health
```

**2. Check Logs**
Look at the terminal where you ran `python3 main.py` for detailed logs:
```
2025-11-17 12:00:45,123 - main - INFO - Processing recipe request
2025-11-17 12:00:46,234 - app_services - INFO - Gemini extracted ingredients
2025-11-17 12:00:47,345 - app_services - INFO - Spoonacular found 10 recipes
```

**3. Verify API Keys**
```bash
# Check environment variables are set
echo $GOOGLE_API_KEY
echo $SPOONACULAR_API_KEY
```

**4. Test with Simpler Input**
```bash
# Try minimal request
curl -X POST http://localhost:5001/api/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "height_cm": 180,
    "weight_kg": 75,
    "allergies": [],
    "food_preferences": "chicken",
    "diet_goals": "healthy"
  }'
```

---

## Performance & Limitations

### Response Time
- Health check: ~10ms
- Recipe request: 8-15 seconds (includes external API calls)
  - Gemini ingredient parsing: ~2-3s
  - Spoonacular search: ~1-2s
  - Recipe enrichment (15 recipes × 2 calls each): ~5-10s

### API Limits
- **Gemini**: 60 requests/minute (free tier)
- **Spoonacular**: 150 requests/day (free tier)
  - Current backend uses ~31 API calls per recipe request
  - Free tier allows ~4-5 recipe requests per day

### Resource Usage
- Memory: ~150-200 MB baseline
- CPU: Minimal (mostly waiting for I/O)
- Network: Limited by external API calls

---

## Code Overview

### `main.py`
Flask application entry point. Defines:
- `/health` - Health check endpoint
- `/api/recipes` - Main recipe endpoint
- Error handlers (400, 404, 500)
- CORS configuration
- Request/response logging

### `app_models.py`
Data models and validation:
- `UserInput` - Validates and parses user input
- `UserMetrics` - Calculates BMI, TDEE, macro targets
- `Recipe` - Represents a recipe with all metadata
- `RecipeNutrition` - Parses nutritional information
- `RecipePricing` - Parses pricing information
- Custom exceptions: `ValidationError`, `APIError`, `ExternalAPIError`

### `app_services.py`
Business logic:
- `GeminiService` - Communicates with Google Gemini API
- `SpoonacularService` - Communicates with Spoonacular API (with caching)
- `RecipeService` - Orchestrates the full workflow

### `test_backend.py`
Automated tests covering:
- Input validation (valid/invalid cases)
- User metrics calculation
- Nutrition parsing
- Pricing parsing
- Macro alignment scoring

---

## Development Notes

- Backend is localhost-only by default (CORS configured for localhost:3000)
- To use with a different frontend, update `NETLIFY_DOMAIN` in `.env`
- All inputs are validated server-side; never trust frontend validation
- Recipes are sorted by macro alignment score first, then by cost
- Allergen filtering is conservative: any match = recipe excluded
- Pricing is optional; recipes are returned even if pricing unavailable

---

## Dependencies

- **Flask 3.0.3** - Web framework
- **flask-cors 4.0.0** - CORS support
- **python-dotenv 1.0.1** - Environment variable management
- **google-genai 1.10.0** - Google Gemini API client
- **requests 2.32.2** - HTTP client
- **gunicorn 21.2.0** - Production server (if deploying)

See `requirements.txt` for exact versions and commands to install.

---

## Support

For issues or questions:
1. Check the **Troubleshooting** section above
2. Review the logs in the terminal where you ran `python3 main.py`
3. Try running `test_backend.py` to verify backend functionality
4. Check that API keys are valid and have remaining quota

---

## License

Educational project for CSCI 6221
