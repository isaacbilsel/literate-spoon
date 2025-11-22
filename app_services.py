"""
Service layer for external API calls and business logic.
Handles Gemini, Spoonacular, and calculations.
"""

import logging
from typing import List, Dict, Any, Optional
import requests
from google import genai
from app_models import (
    UserInput, UserMetrics, Recipe, RecipeNutrition, RecipePricing,
    ValidationError, ExternalAPIError, GeneratedMealPlan, DayMeals, Meal
)

logger = logging.getLogger(__name__)


class GeminiService:
    """Handle all Gemini AI API calls."""
    
    def __init__(self, api_key: str):
        """Initialize Gemini client."""
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash"
    
    def parse_ingredients_with_constraints(
        self,
        food_preferences: str,
        diet_goals: str,
        allergies: List[str]
    ) -> str:
        """
        Use Gemini to extract ingredients considering allergies and preferences.
        
        Args:
            food_preferences: User's food preferences
            diet_goals: User's dietary goals
            allergies: List of allergens to exclude
            
        Returns:
            Comma-separated ingredient list
            
        Raises:
            ExternalAPIError: If Gemini API call fails
        """
        try:
            # Build allergy constraint string
            allergy_str = ", ".join(allergies) if allergies else "none"
            
            prompt = f"""You are a recipe ingredient extractor. The user has provided:
            
Dietary Goals: {diet_goals}
Food Preferences: {food_preferences}
ALLERGIES TO EXCLUDE: {allergy_str}

Your task:
1. Extract ingredients suitable for the stated goals and preferences
2. ABSOLUTELY DO NOT include any of the allergenic ingredients
3. Return ONLY a comma-separated list of ingredients
4. Example format: "chicken,broccoli,olive oil,garlic"

CRITICAL: Do not include {allergy_str} in any form. Return ONLY the ingredient list, nothing else."""
            
            chat = self.client.chats.create(model=self.model)
            response = chat.send_message(prompt)
            ingredients_str = response.text.strip()
            
            if not ingredients_str or ingredients_str.lower() in ["none", "no ingredients"]:
                raise ExternalAPIError("Gemini could not extract meaningful ingredients from the provided input")
            
            logger.info(f"Gemini extracted ingredients: {ingredients_str[:100]}...")
            return ingredients_str
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise ExternalAPIError(f"Gemini API error: {str(e)}")


class SpoonacularService:
    """Handle all Spoonacular API calls with caching."""
    
    BASE_URL = "https://api.spoonacular.com"
    REQUEST_TIMEOUT = 10
    
    def __init__(self, api_key: str):
        """Initialize Spoonacular service."""
        self.api_key = api_key
        self._recipe_cache = {}  # Simple in-memory cache
    
    def search_recipes_by_ingredients(
        self,
        ingredients: str,
        number: int = 10,
        ranking: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Search recipes by ingredients.
        
        Args:
            ingredients: Comma-separated ingredient list
            number: Number of recipes to return
            ranking: 1 = maximize used ingredients, 2 = minimize missing
            
        Returns:
            List of recipe objects with id, title, image, ingredients
            
        Raises:
            ExternalAPIError: If API call fails
        """
        try:
            url = f"{self.BASE_URL}/recipes/findByIngredients"
            params = {
                "ingredients": ingredients,
                "number": number,
                "ranking": ranking,
                "apiKey": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            recipes = response.json()
            logger.info(f"Spoonacular found {len(recipes)} recipes")
            return recipes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Spoonacular search error: {str(e)}")
            raise ExternalAPIError(f"Spoonacular search failed: {str(e)}")
    
    def get_recipe_information(self, recipe_id: int) -> Dict[str, Any]:
        """
        Get detailed information for a recipe (including nutrition).
        
        Args:
            recipe_id: Spoonacular recipe ID
            
        Returns:
            Recipe information including nutrition data
            
        Raises:
            ExternalAPIError: If API call fails
        """
        try:
            # Check cache first
            if recipe_id in self._recipe_cache:
                return self._recipe_cache[recipe_id]
            
            url = f"{self.BASE_URL}/recipes/{recipe_id}/information"
            params = {
                "includeNutrition": True,
                "apiKey": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            info = response.json()
            self._recipe_cache[recipe_id] = info
            return info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Spoonacular info error for recipe {recipe_id}: {str(e)}")
            raise ExternalAPIError(f"Failed to fetch recipe details: {str(e)}")
    
    def get_recipe_price_breakdown(self, recipe_id: int) -> Dict[str, Any]:
        """
        Get price breakdown for a recipe.
        
        Args:
            recipe_id: Spoonacular recipe ID
            
        Returns:
            Price breakdown data
            
        Raises:
            ExternalAPIError: If API call fails
        """
        try:
            url = f"{self.BASE_URL}/recipes/{recipe_id}/priceBreakdown"
            params = {"apiKey": self.api_key}

            response = requests.get(url, params=params, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            # Some recipes do not have price breakdown data (404). Treat as optional and return None.
            status = None
            if e.response is not None:
                status = e.response.status_code

            if status == 404:
                logger.info(f"Spoonacular price data not found for recipe {recipe_id} (404). Skipping pricing for this recipe.")
                return {}
            else:
                logger.warning(f"Spoonacular price HTTP error for recipe {recipe_id}: {str(e)}")
                return {}

        except requests.exceptions.RequestException as e:
            logger.error(f"Spoonacular price error for recipe {recipe_id}: {str(e)}")
            # Price is optional - log but don't raise
            return {}
    
    def enrich_recipe(
        self,
        basic_recipe: Dict[str, Any],
        allergies: List[str]
    ) -> Optional[Recipe]:
        """
        Enrich a basic recipe with nutrition and pricing.
        Also filter out recipes containing allergens.
        
        Args:
            basic_recipe: Recipe from search results
            allergies: List of allergens to check
            
        Returns:
            Enriched Recipe object or None if contains allergen
        """
        try:
            recipe_id = basic_recipe.get("id")
            
            # Get full recipe info (includes nutrition)
            try:
                full_info = self.get_recipe_information(recipe_id)
            except ExternalAPIError as e:
                logger.warning(f"Could not fetch full info for {recipe_id}: {e}")
                full_info = basic_recipe
            
            # Check for allergens in all ingredients
            all_ingredients = []
            if "extendedIngredients" in full_info:
                for ingredient in full_info["extendedIngredients"]:
                    ingredient_name = ingredient.get("original", "").lower()
                    all_ingredients.append(ingredient_name)
                    
                    # Check if any allergen is in this ingredient
                    for allergen in allergies:
                        if allergen.lower() in ingredient_name:
                            logger.info(f"Filtering out recipe {recipe_id}: contains allergen '{allergen}'")
                            return None
            
            # Extract nutrition
            nutrition = None
            if "nutrition" in full_info and full_info["nutrition"].get("nutrients"):
                nutrition = RecipeNutrition.from_spoonacular(full_info["nutrition"])
            
            # Get pricing
            pricing = None
            try:
                price_data = self.get_recipe_price_breakdown(recipe_id)
                servings = full_info.get("servings", 1)
                pricing = RecipePricing.from_spoonacular(price_data, servings)
            except ExternalAPIError:
                pass  # Pricing is optional
            
            # Create enriched recipe
            recipe = Recipe(
                id=recipe_id,
                title=basic_recipe.get("title", "Unknown"),
                image=basic_recipe.get("image", ""),
                used_ingredients=[i.get("name", "") for i in basic_recipe.get("usedIngredients", [])],
                missed_ingredients=[i.get("name", "") for i in basic_recipe.get("missedIngredients", [])],
                macronutrients=nutrition,
                pricing=pricing
            )
            
            return recipe
            
        except Exception as e:
            logger.error(f"Error enriching recipe {basic_recipe.get('id')}: {str(e)}")
            return None


class UserMetricsService:
    """Calculate user health metrics."""
    
    @staticmethod
    def calculate_metrics(user_input: UserInput) -> UserMetrics:
        """
        Calculate user metrics from input.
        
        Args:
            user_input: Validated user input
            
        Returns:
            UserMetrics object
        """
        return UserMetrics.calculate(user_input)


class RecipeService:
    """High-level recipe orchestration."""
    
    def __init__(self, gemini_service: GeminiService, spoonacular_service: SpoonacularService):
        """Initialize with dependencies."""
        self.gemini = gemini_service
        self.spoonacular = spoonacular_service
    
    def get_recipes_for_user(
        self,
        user_input: UserInput,
        limit: int = 8
    ) -> tuple[str, List[Recipe], UserMetrics]:
        """
        Complete workflow: validate → parse → search → enrich → filter → sort.
        
        Args:
            user_input: Validated user input
            limit: Maximum recipes to return
            
        Returns:
            Tuple of (parsed_ingredients, recipe_list, user_metrics)
            
        Raises:
            ExternalAPIError: If external API calls fail
        """
        # Calculate user metrics
        metrics = UserMetricsService.calculate_metrics(user_input)
        logger.info(f"Calculated metrics - BMI: {metrics.bmi}, TDEE: {metrics.tdee_estimate}")
        
        # Step 1: Extract ingredients with Gemini
        parsed_ingredients = self.gemini.parse_ingredients_with_constraints(
            user_input.food_preferences,
            user_input.diet_goals,
            user_input.allergies
        )
        logger.info(f"Parsed ingredients: {parsed_ingredients}")
        
        # Step 2: Search recipes
        basic_recipes = self.spoonacular.search_recipes_by_ingredients(
            parsed_ingredients,
            number=15  # Get more to account for filtering
        )
        
        if not basic_recipes:
            logger.warning("No recipes found from Spoonacular")
            return parsed_ingredients, [], metrics
        
        # Step 3: Enrich recipes and filter for allergens
        enriched_recipes = []
        for basic_recipe in basic_recipes:
            recipe = self.spoonacular.enrich_recipe(basic_recipe, user_input.allergies)
            if recipe:
                enriched_recipes.append(recipe)
        
        logger.info(f"Enriched {len(enriched_recipes)} recipes (after allergen filtering)")
        
        # Step 4: Calculate macro alignment and sort
        for recipe in enriched_recipes:
            recipe.macro_alignment_score = recipe.calculate_macro_alignment(metrics.macro_targets)
        
        # Sort by: (1) macro alignment score, (2) cost (low to high)
        sorted_recipes = sorted(
            enriched_recipes,
            key=lambda r: (
                -r.macro_alignment_score,  # Higher score first
                r.pricing.cost_per_serving if r.pricing else float('inf')  # Lower cost first
            )
        )
        
        # Return top N
        final_recipes = sorted_recipes[:limit]
        logger.info(f"Returning {len(final_recipes)} recipes")
        
        return parsed_ingredients, final_recipes, metrics


class MealPlanService:
    """Service for generating AI-powered meal plans."""
    
    def __init__(self, gemini_service: GeminiService, spoonacular_service: SpoonacularService):
        self.gemini_service = gemini_service
        self.spoonacular_service = spoonacular_service
    
    def generate_weekly_meal_plan(
        self,
        budget: float,
        allergies: List[str],
        diet_goals: str,
        food_preferences: str = "",
        target_calories_per_day: int = 2000
    ) -> GeneratedMealPlan:
        """
        Generate a complete weekly meal plan using Gemini AI and Spoonacular.
        
        Args:
            budget: Weekly budget for meals
            allergies: List of allergens to exclude
            diet_goals: User's dietary objectives
            food_preferences: User's food preferences
            target_calories_per_day: Target daily calories
            
        Returns:
            GeneratedMealPlan object with structured meal data
            
        Raises:
            ExternalAPIError: If API calls fail
        """
        try:
            import json
            from datetime import datetime, timedelta
            import uuid
            
            # Create the Gemini prompt for meal plan generation
            allergy_str = ", ".join(allergies) if allergies else "none"
            daily_budget = budget / 7  # Distribute weekly budget across 7 days
            
            prompt = f"""You are an expert meal planning nutritionist. Create a 7-day meal plan with the following constraints:

Weekly Budget: ${budget:.2f} (approximately ${daily_budget:.2f} per day)
Allergies to EXCLUDE: {allergy_str}
Diet Goals: {diet_goals}
Food Preferences: {food_preferences or "none specified"}
Target Calories per Day: {target_calories_per_day}

Create a JSON response with this EXACT structure:
{{
  "days": [
    {{
      "day": "Monday",
      "breakfast": {{
        "name": "meal name",
        "description": "brief description",
        "calories": 400,
        "protein": 20.5,
        "carbs": 45.0,
        "fat": 15.0
      }},
      "lunch": {{
        "name": "meal name",
        "description": "brief description", 
        "calories": 600,
        "protein": 30.0,
        "carbs": 60.0,
        "fat": 20.0
      }},
      "dinner": {{
        "name": "meal name",
        "description": "brief description",
        "calories": 800,
        "protein": 40.0,
        "carbs": 80.0,
        "fat": 25.0
      }},
      "snacks": [
        {{
          "name": "snack name",
          "description": "brief description",
          "calories": 200,
          "protein": 10.0,
          "carbs": 20.0,
          "fat": 8.0
        }}
      ]
    }}
  ]
}}

Requirements:
1. NEVER include {allergy_str} ingredients
2. Each meal should be realistic and achievable within the budget
3. Meals should align with the diet goals: {diet_goals}
4. Total daily calories should be close to {target_calories_per_day}
5. Include all 7 days: Monday through Sunday
6. Provide realistic nutritional values
7. Return ONLY valid JSON, no additional text

Generate the meal plan now:"""

            # Get meal plan from Gemini
            chat = self.gemini_service.client.chats.create(model=self.gemini_service.model)
            response = chat.send_message(prompt)
            
            # Parse the JSON response
            try:
                meal_plan_data = json.loads(response.text.strip())
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it's wrapped in text
                import re
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    meal_plan_data = json.loads(json_match.group())
                else:
                    raise ExternalAPIError("Gemini returned invalid JSON format")
            
            # Convert to our data structures
            days = []
            total_weekly_calories = 0
            
            for day_data in meal_plan_data.get("days", []):
                # Create meals
                breakfast = Meal(
                    name=day_data["breakfast"]["name"],
                    description=day_data["breakfast"].get("description"),
                    calories=day_data["breakfast"].get("calories"),
                    protein=day_data["breakfast"].get("protein"),
                    carbs=day_data["breakfast"].get("carbs"),
                    fat=day_data["breakfast"].get("fat")
                )
                
                lunch = Meal(
                    name=day_data["lunch"]["name"],
                    description=day_data["lunch"].get("description"),
                    calories=day_data["lunch"].get("calories"),
                    protein=day_data["lunch"].get("protein"),
                    carbs=day_data["lunch"].get("carbs"),
                    fat=day_data["lunch"].get("fat")
                )
                
                dinner = Meal(
                    name=day_data["dinner"]["name"],
                    description=day_data["dinner"].get("description"),
                    calories=day_data["dinner"].get("calories"),
                    protein=day_data["dinner"].get("protein"),
                    carbs=day_data["dinner"].get("carbs"),
                    fat=day_data["dinner"].get("fat")
                )
                
                # Handle snacks
                snacks = []
                if "snacks" in day_data and day_data["snacks"]:
                    for snack_data in day_data["snacks"]:
                        snack = Meal(
                            name=snack_data["name"],
                            description=snack_data.get("description"),
                            calories=snack_data.get("calories"),
                            protein=snack_data.get("protein"),
                            carbs=snack_data.get("carbs"),
                            fat=snack_data.get("fat")
                        )
                        snacks.append(snack)
                
                # Create day meals
                day_meals = DayMeals(
                    day=day_data["day"],
                    breakfast=breakfast,
                    lunch=lunch,
                    dinner=dinner,
                    snacks=snacks if snacks else None
                )
                
                days.append(day_meals)
                
                # Calculate daily calories
                day_calories = (breakfast.calories or 0) + (lunch.calories or 0) + (dinner.calories or 0)
                day_calories += sum(snack.calories or 0 for snack in snacks)
                total_weekly_calories += day_calories
            
            # Create the final meal plan
            start_date = datetime.now()
            end_date = start_date + timedelta(days=6)
            
            meal_plan = GeneratedMealPlan(
                id=str(uuid.uuid4()),
                name=f"AI Generated Meal Plan - {start_date.strftime('%Y-%m-%d')}",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                is_current=True,
                days=days,
                total_calories=total_weekly_calories,
                created_at=datetime.now().isoformat()
            )
            
            logger.info(f"Generated meal plan with {len(days)} days, total calories: {total_weekly_calories}")
            return meal_plan
            
        except Exception as e:
            logger.error(f"Meal plan generation error: {str(e)}")
            raise ExternalAPIError(f"Failed to generate meal plan: {str(e)}")
