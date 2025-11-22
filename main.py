"""Flask app entrypoint for Literate Spoon.

This file wires up the Flask app, JWT helpers, DB session handling,
and the main endpoints used by the frontend. It fixes prior issues with
duplicated decorators and misplaced functions by providing a single
definition for each auth endpoint.
"""

import os
import logging
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from dotenv import load_dotenv
import jwt
from app_models import (
    UserInput,
    ValidationError,
    APIError,
    ExternalAPIError,
    User,
    Profile,
    MealPlan,
    GroceryList,
    ChatMessage,
    SessionLocal,
    init_db,
    GeneratedMealPlan,
    DayMeals,
    Meal,
)
from app_services import GeminiService, SpoonacularService, RecipeService, MealPlanService

load_dotenv()
init_db()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_secret")

# CORS configuration - configure for production
CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "OPTIONS"]
cors_config = {
    "origins": "*",
    "methods": CORS_METHODS,
    "allow_headers": ["Content-Type", "Authorization"],
    "max_age": 3600,
}
CORS(app, resources={r"/api/*": cors_config})

# Initialize services
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

if not GOOGLE_API_KEY or not SPOONACULAR_API_KEY:
    logger.warning("Missing API keys - app may not function fully in dev")

gemini_service = GeminiService(GOOGLE_API_KEY)
spoonacular_service = SpoonacularService(SPOONACULAR_API_KEY)
recipe_service = RecipeService(gemini_service, spoonacular_service)
meal_plan_service = MealPlanService(gemini_service, spoonacular_service)

start_time = datetime.now()


# JWT helpers
def create_access_token(user_id, role, expires_delta=None):
    # Default expiration: 2 days (if not provided)
    if expires_delta is None:
        expires_delta = timedelta(days=2)
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + expires_delta,
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def decode_access_token(token):
    try:
        return jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_db():
    if "db" not in g:
        g.db = SessionLocal()
    return g.db


@app.teardown_appcontext
def remove_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_current_user():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        return None
    db = get_db()
    return db.query(User).filter(User.id == payload.get("user_id")).first()


# --- AUTH ENDPOINTS ---
@app.route("/api/auth/register", methods=["POST"])
def register():
    db = get_db()
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    first_name = data.get("firstName")
    gender = data.get("gender")
    zip_code = data.get("zipCode")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    if db.query(User).filter(User.email == email).first():
        return jsonify({"error": "Email already exists"}), 409

    password_hash = User.hash_password(password)
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)

    # create profile if provided
    profile = Profile(user_id=user.id, first_name=first_name, gender=gender, zip_code=zip_code)
    db.add(profile)
    db.commit()

    access_token = create_access_token(user.id, user.role)
    return (
        jsonify({
            "user": {"id": user.id, "email": user.email},
            "accessToken": access_token,
            "refreshTokenSetCookie": False,
        }),
        201,
    )


@app.route("/api/auth/login", methods=["POST"])
def login():
    db = get_db()
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.verify_password(password):
        return jsonify({"error": "Incorrect credentials"}), 401

    access_token = create_access_token(user.id, user.role)
    user.last_login = datetime.utcnow()
    db.commit()

    return (
        jsonify({
            "user": {"id": user.id, "email": user.email},
            "accessToken": access_token,
            "refreshTokenSetCookie": False,
        }),
        200,
    )


@app.route("/api/auth/me", methods=["GET"])
def get_current_user_info():
    """Get current authenticated user's info."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    
    return jsonify({
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "profile": profile.to_dict() if profile else None,
    }), 200


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Logout endpoint (JWT is stateless, so this is mainly for frontend)."""
    return jsonify({"message": "Logged out successfully"}), 200


@app.route("/api/auth/refresh", methods=["POST"])
def refresh_token():
    """Refresh access token using current JWT."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    new_access_token = create_access_token(user.id, user.role)
    return jsonify({
        "accessToken": new_access_token,
        "refreshTokenSetCookie": False,
    }), 200


# --- PROFILE ENDPOINTS ---
@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Get user profile."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    
    return jsonify(profile.to_dict()), 200


@app.route("/api/profile", methods=["PUT", "PATCH"])
def update_profile():
    """Update user profile."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    
    data = request.get_json() or {}
    
    # Update allowed fields
    if "firstName" in data:
        profile.first_name = data["firstName"]
    if "gender" in data:
        profile.gender = data["gender"]
    if "zipCode" in data:
        profile.zip_code = data["zipCode"]
    if "bio" in data:
        profile.bio = data["bio"]
    if "dietaryRestrictions" in data:
        profile.dietary_restrictions = data["dietaryRestrictions"]
    if "height_cm" in data:
        profile.height_cm = data["height_cm"]
    if "weight_kg" in data:
        profile.weight_kg = data["weight_kg"]
    if "allergies" in data:
        profile.allergies = json.dumps(data["allergies"])
    if "food_preferences" in data:
        profile.food_preferences = data["food_preferences"]
    if "diet_goals" in data:
        profile.diet_goals = data["diet_goals"]
    
    db.commit()
    
    return jsonify({
        "message": "Profile updated successfully",
        "profile": profile.to_dict(),
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


# --- MEAL PLAN ENDPOINTS ---
@app.route("/api/meal-plans", methods=["GET"])
def list_meal_plans():
    """List all meal plans for authenticated user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    meal_plans = db.query(MealPlan).filter(MealPlan.user_id == user.id).all()
    
    return jsonify({
        "meal_plans": [mp.to_dict() for mp in meal_plans]
    }), 200


@app.route("/api/meal-plans", methods=["POST"])
def create_meal_plan():
    """Create a new meal plan."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    data = request.get_json() or {}
    
    meal_plan = MealPlan(
        user_id=user.id,
        name=data.get("name", "Untitled Meal Plan"),
        description=data.get("description", ""),
        meals=json.dumps(data.get("meals", [])),  # Serialize meals to JSON
    )
    db.add(meal_plan)
    db.commit()
    
    return jsonify({
        "message": "Meal plan created",
        "meal_plan": meal_plan.to_dict(),
    }), 201


@app.route("/api/meal-plans/<int:meal_plan_id>", methods=["GET"])
def get_meal_plan(meal_plan_id):
    """Get a specific meal plan."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    meal_plan = db.query(MealPlan).filter(
        MealPlan.id == meal_plan_id,
        MealPlan.user_id == user.id
    ).first()
    
    if not meal_plan:
        return jsonify({"error": "Meal plan not found"}), 404
    
    return jsonify(meal_plan.to_dict()), 200


@app.route("/api/meal-plans/<int:meal_plan_id>", methods=["PUT", "PATCH"])
def update_meal_plan(meal_plan_id):
    """Update a meal plan."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    meal_plan = db.query(MealPlan).filter(
        MealPlan.id == meal_plan_id,
        MealPlan.user_id == user.id
    ).first()
    
    if not meal_plan:
        return jsonify({"error": "Meal plan not found"}), 404
    
    data = request.get_json() or {}
    
    if "name" in data:
        meal_plan.name = data["name"]
    if "description" in data:
        meal_plan.description = data["description"]
    if "meals" in data:
        meal_plan.meals = json.dumps(data["meals"])
    
    db.commit()
    
    return jsonify({
        "message": "Meal plan updated",
        "meal_plan": meal_plan.to_dict(),
    }), 200


@app.route("/api/meal-plans/<int:meal_plan_id>/activate", methods=["POST"])
def activate_meal_plan(meal_plan_id):
    """Activate a meal plan."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    meal_plan = db.query(MealPlan).filter(
        MealPlan.id == meal_plan_id,
        MealPlan.user_id == user.id
    ).first()
    
    if not meal_plan:
        return jsonify({"error": "Meal plan not found"}), 404
    
    # Deactivate all other meal plans
    db.query(MealPlan).filter(
        MealPlan.user_id == user.id,
        MealPlan.id != meal_plan_id
    ).update({"is_active": False})
    
    meal_plan.is_active = True
    db.commit()
    
    return jsonify({
        "message": "Meal plan activated",
        "meal_plan": meal_plan.to_dict(),
    }), 200


@app.route("/api/meal-plans/<int:meal_plan_id>/grocery-list", methods=["GET"])
def get_meal_plan_grocery_list(meal_plan_id):
    """Get grocery list for a meal plan."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    grocery_list = db.query(GroceryList).filter(
        GroceryList.meal_plan_id == meal_plan_id,
        GroceryList.user_id == user.id
    ).first()
    
    if not grocery_list:
        return jsonify({"error": "Grocery list not found"}), 404
    
    return jsonify(grocery_list.to_dict()), 200


@app.route("/api/meal-plans/generate", methods=["POST"])
def generate_meal_plan():
    """Generate a new AI-powered meal plan based on user preferences and budget."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        db = get_db()
        data = request.get_json() or {}
        
        # Get user's profile for personalized recommendations
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        
        # Extract parameters from request
        budget = data.get("budget", 100.0)  # Default weekly budget
        allergies = data.get("allergies", [])
        diet_goals = data.get("dietGoals", "")
        food_preferences = data.get("foodPreferences", "")
        target_calories = data.get("targetCalories", 2000)
        
        # Use profile data if available and not overridden
        if profile:
            if not allergies and profile.allergies:
                try:
                    allergies = json.loads(profile.allergies)
                except Exception:
                    allergies = []
            
            if not diet_goals and profile.diet_goals:
                diet_goals = profile.diet_goals
                
            if not food_preferences and profile.food_preferences:
                food_preferences = profile.food_preferences
        
        # Validate required parameters
        if not diet_goals:
            return jsonify({
                "error": "Diet goals are required. Please specify your dietary objectives."
            }), 400
        
        if budget <= 0:
            return jsonify({
                "error": "Budget must be a positive number."
            }), 400
        
        logger.info(f"Generating meal plan for user {user.id} - Budget: ${budget}, Diet goals: {diet_goals}")
        
        # Generate the meal plan using AI
        generated_meal_plan = meal_plan_service.generate_weekly_meal_plan(
            budget=budget,
            allergies=allergies,
            diet_goals=diet_goals,
            food_preferences=food_preferences,
            target_calories_per_day=target_calories
        )
        
        # Optionally save to database as a regular MealPlan
        if data.get("saveToDatabase", True):
            meal_plan_db = MealPlan(
                user_id=user.id,
                name=generated_meal_plan.name,
                description=f"AI-generated meal plan for budget ${budget}/week with goals: {diet_goals}",
                meals=json.dumps(generated_meal_plan.to_dict())
            )
            db.add(meal_plan_db)
            db.commit()
            
            # Update the generated meal plan ID to match the database ID
            generated_meal_plan.id = str(meal_plan_db.id)
        
        logger.info(f"Successfully generated meal plan with {len(generated_meal_plan.days)} days")
        
        return jsonify({
            "success": True,
            "meal_plan": generated_meal_plan.to_dict()
        }), 200
        
    except ExternalAPIError as e:
        logger.error(f"External API error during meal plan generation: {e.message}")
        return jsonify({
            "success": False,
            "error": e.message,
            "type": "external_api_error"
        }), 500
        
    except Exception as e:
        logger.exception(f"Unexpected error in meal plan generation: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error during meal plan generation",
            "type": "internal_error"
        }), 500


@app.route("/api/meal-plans/generated", methods=["GET"])
def get_generated_meal_plans():
    """Get all AI-generated meal plans for authenticated user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        db = get_db()
        
        # Query meal plans that contain AI-generated data (indicated by description containing "AI-generated")
        meal_plans = db.query(MealPlan).filter(
            MealPlan.user_id == user.id,
            MealPlan.description.contains("AI-generated")
        ).order_by(MealPlan.created_at.desc()).all()
        
        generated_meal_plans = []
        
        for meal_plan in meal_plans:
            try:
                # Parse the stored JSON data which contains the full GeneratedMealPlan structure
                if meal_plan.meals:
                    meal_data = json.loads(meal_plan.meals)
                    
                    # If it's a nested structure (GeneratedMealPlan was stored as JSON), extract it
                    if isinstance(meal_data, dict) and 'id' in meal_data and 'days' in meal_data:
                        # This is a full GeneratedMealPlan object
                        generated_meal_plans.append(meal_data)
                    else:
                        # This might be a regular meal plan, convert to GeneratedMealPlan format
                        generated_meal_plans.append({
                            "id": str(meal_plan.id),
                            "name": meal_plan.name,
                            "description": meal_plan.description,
                            "startDate": meal_plan.created_at.strftime("%Y-%m-%d") if meal_plan.created_at else "",
                            "endDate": "",
                            "isActive": meal_plan.is_active,
                            "days": meal_data if isinstance(meal_data, list) else [],
                            "weeklyBudget": 0.0,
                            "totalCalories": 0,
                            "totalProtein": 0.0,
                            "totalCarbs": 0.0,
                            "totalFat": 0.0
                        })
                        
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse meal plan {meal_plan.id} data: {e}")
                continue
        
        logger.info(f"Retrieved {len(generated_meal_plans)} generated meal plans for user {user.id}")
        
        return jsonify({
            "success": True,
            "count": len(generated_meal_plans),
            "meal_plans": generated_meal_plans
        }), 200
        
    except Exception as e:
        logger.exception(f"Unexpected error retrieving generated meal plans: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error retrieving meal plans",
            "type": "internal_error"
        }), 500


# --- GROCERY LIST ENDPOINTS ---
@app.route("/api/grocery-lists", methods=["GET"])
def list_grocery_lists():
    """List all grocery lists for authenticated user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    grocery_lists = db.query(GroceryList).filter(GroceryList.user_id == user.id).all()
    
    return jsonify({
        "grocery_lists": [gl.to_dict() for gl in grocery_lists]
    }), 200


@app.route("/api/grocery-lists", methods=["POST"])
def create_grocery_list():
    """Create a new grocery list."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    data = request.get_json() or {}
    
    grocery_list = GroceryList(
        user_id=user.id,
        meal_plan_id=data.get("mealPlanId"),
        items=json.dumps(data.get("items", [])) if isinstance(data.get("items"), list) else data.get("items", "[]"),
    )
    db.add(grocery_list)
    db.commit()
    
    return jsonify({
        "message": "Grocery list created",
        "grocery_list": grocery_list.to_dict(),
    }), 201


@app.route("/api/grocery-lists/<int:grocery_list_id>", methods=["GET"])
def get_grocery_list(grocery_list_id):
    """Get a specific grocery list."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    grocery_list = db.query(GroceryList).filter(
        GroceryList.id == grocery_list_id,
        GroceryList.user_id == user.id
    ).first()
    
    if not grocery_list:
        return jsonify({"error": "Grocery list not found"}), 404
    
    return jsonify(grocery_list.to_dict()), 200


@app.route("/api/grocery-lists/<int:grocery_list_id>", methods=["PUT", "PATCH"])
def update_grocery_list(grocery_list_id):
    """Update a grocery list."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    grocery_list = db.query(GroceryList).filter(
        GroceryList.id == grocery_list_id,
        GroceryList.user_id == user.id
    ).first()
    
    if not grocery_list:
        return jsonify({"error": "Grocery list not found"}), 404
    
    data = request.get_json() or {}
    
    if "items" in data:
        grocery_list.items = json.dumps(data["items"]) if isinstance(data["items"], list) else data["items"]
    
    db.commit()
    
    return jsonify({
        "message": "Grocery list updated",
        "grocery_list": grocery_list.to_dict(),
    }), 200


# --- CHAT ENDPOINTS ---
@app.route("/api/chat/parse", methods=["POST"])
def parse_chat():
    """Parse user chat message and return response."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    data = request.get_json() or {}
    message = data.get("message", "")
    
    if not message:
        return jsonify({"error": "Message required"}), 400
    
    # Simple placeholder response
    response = f"I received your message: '{message}'. How can I help with your meal plan?"
    
    # Store chat message
    chat_msg = ChatMessage(
        user_id=user.id,
        message=message,
        response=response,
    )
    db.add(chat_msg)
    db.commit()
    
    return jsonify({
        "message": message,
        "response": response,
        "chat_id": chat_msg.id,
    }), 200


@app.route("/api/chat/history", methods=["GET"])
def get_chat_history():
    """Get chat history for authenticated user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    messages = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).all()
    
    return jsonify({
        "chat_history": [msg.to_dict() for msg in messages]
    }), 200


# --- UTILITY ENDPOINTS ---
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for deployment monitoring."""
    uptime_seconds = (datetime.now() - start_time).total_seconds()
    return jsonify({
        "status": "ok",
        "uptime_seconds": int(uptime_seconds),
        "timestamp": datetime.now().isoformat()
    }), 200


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
    logger.info("CORS allowed origins: * (all sites)")
    logger.info(f"Gemini API: {'configured' if GOOGLE_API_KEY else 'NOT SET'}")
    logger.info(f"Spoonacular API: {'configured' if SPOONACULAR_API_KEY else 'NOT SET'}")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
