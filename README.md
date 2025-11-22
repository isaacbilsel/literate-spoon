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
---
