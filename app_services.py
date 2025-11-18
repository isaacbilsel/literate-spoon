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
    ValidationError, ExternalAPIError
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
