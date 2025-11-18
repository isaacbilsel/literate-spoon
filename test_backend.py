#!/usr/bin/env python3
"""
Local testing script for the recipe recommendation backend.
Run this to validate all core functionality works before deployment.
"""

import json
from app_models import UserInput, UserMetrics, Recipe, RecipeNutrition, RecipePricing, ValidationError

def test_user_input_validation():
    """Test input validation."""
    print("\n=== Testing UserInput Validation ===")
    
    # Valid input
    try:
        user = UserInput.from_dict({
            "height_cm": 180,
            "weight_kg": 75,
            "allergies": ["peanuts", "shellfish"],
            "food_preferences": "Mediterranean, high protein",
            "diet_goals": "weight loss, build muscle"
        })
        print("✓ Valid input accepted")
        print(f"  Height: {user.height_cm} cm, Weight: {user.weight_kg} kg")
        print(f"  Allergies: {user.allergies}")
    except ValidationError as e:
        print(f"✗ Valid input rejected: {e.message}")
        return False
    
    # Invalid height (too low)
    try:
        UserInput.from_dict({
            "height_cm": 50,
            "weight_kg": 75,
            "allergies": [],
            "food_preferences": "test",
            "diet_goals": "test"
        })
        print("✗ Should have rejected height 50 cm")
        return False
    except ValidationError as e:
        print(f"✓ Correctly rejected invalid height: {e.message}")
    
    # Invalid weight (too high)
    try:
        UserInput.from_dict({
            "height_cm": 180,
            "weight_kg": 350,
            "allergies": [],
            "food_preferences": "test",
            "diet_goals": "test"
        })
        print("✗ Should have rejected weight 350 kg")
        return False
    except ValidationError as e:
        print(f"✓ Correctly rejected invalid weight: {e.message}")
    
    # Too many allergies
    try:
        UserInput.from_dict({
            "height_cm": 180,
            "weight_cm": 75,
            "allergies": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"],
            "food_preferences": "test",
            "diet_goals": "test"
        })
        print("✗ Should have rejected 11 allergies")
        return False
    except ValidationError as e:
        print(f"✓ Correctly rejected too many allergies: {e.message}")
    
    return True


def test_user_metrics():
    """Test BMI and TDEE calculations."""
    print("\n=== Testing UserMetrics Calculation ===")
    
    user = UserInput.from_dict({
        "height_cm": 180,
        "weight_kg": 75,
        "allergies": [],
        "food_preferences": "Mediterranean",
        "diet_goals": "weight loss"
    })
    
    metrics = UserMetrics.calculate(user)
    
    # Check BMI
    expected_bmi = 75 / (1.8 ** 2)
    if abs(metrics.bmi - expected_bmi) < 0.1:
        print(f"✓ BMI calculation correct: {metrics.bmi} (expected {expected_bmi:.1f})")
    else:
        print(f"✗ BMI calculation wrong: {metrics.bmi} (expected {expected_bmi:.1f})")
        return False
    
    # Check TDEE is reasonable (should be 1500-3500 for average person)
    if 1500 < metrics.tdee_estimate < 3500:
        print(f"✓ TDEE estimate reasonable: {metrics.tdee_estimate} kcal/day")
    else:
        print(f"✗ TDEE estimate unreasonable: {metrics.tdee_estimate}")
        return False
    
    # Check macro targets for weight loss goal (30% protein, 40% carbs, 30% fats)
    protein_percent = (metrics.macro_targets["protein_g"] * 4) / metrics.tdee_estimate * 100
    if 25 < protein_percent < 35:
        print(f"✓ Protein correct for weight loss (~30%): {metrics.macro_targets['protein_g']}g")
    else:
        print(f"✗ Protein percentage wrong for weight loss goal: {protein_percent:.1f}%")
        return False
    
    # Check macro targets for muscle gain goal
    user_muscle = UserInput.from_dict({
        "height_cm": 180,
        "weight_kg": 75,
        "allergies": [],
        "food_preferences": "high protein",
        "diet_goals": "build muscle and gain"
    })
    metrics_muscle = UserMetrics.calculate(user_muscle)
    
    if metrics_muscle.macro_targets["carbs_g"] > metrics_muscle.macro_targets["fats_g"]:
        print(f"✓ Carb-heavy for muscle gain: {metrics_muscle.macro_targets['carbs_g']}g carbs")
    else:
        print(f"✗ Carbs not prioritized for muscle gain goal")
        return False
    
    return True


def test_recipe_nutrition():
    """Test recipe nutrition parsing."""
    print("\n=== Testing RecipeNutrition ===")
    
    # Mock Spoonacular nutrition response
    nutrition_data = {
        "nutrients": [
            {"name": "Calories", "amount": 450},
            {"name": "Protein", "amount": 55.2},
            {"name": "Carbohydrates", "amount": 25.1},
            {"name": "Fat", "amount": 15.3}
        ]
    }
    
    nutrition = RecipeNutrition.from_spoonacular(nutrition_data)
    
    if nutrition and nutrition.calories == 450:
        print(f"✓ Nutrition parsed correctly: {nutrition.calories} cal, {nutrition.protein_g}g protein")
    else:
        print(f"✗ Nutrition parsing failed")
        return False
    
    # Test JSON serialization
    nutrition_dict = nutrition.to_dict()
    if "calories" in nutrition_dict and "protein_g" in nutrition_dict:
        print(f"✓ Nutrition serializes to JSON correctly")
    else:
        print(f"✗ Nutrition JSON serialization failed")
        return False
    
    return True


def test_recipe_pricing():
    """Test recipe pricing parsing."""
    print("\n=== Testing RecipePricing ===")
    
    # Mock Spoonacular pricing response (returns cents)
    price_data = {
        "totalCost": 1400  # $14.00 in cents
    }
    
    pricing = RecipePricing.from_spoonacular(price_data, servings=4)
    
    if pricing and abs(pricing.cost_per_serving - 3.5) < 0.01:
        print(f"✓ Pricing calculated correctly: ${pricing.cost_per_serving:.2f} per serving")
    else:
        print(f"✗ Pricing calculation failed: {pricing.cost_per_serving if pricing else 'None'}")
        return False
    
    # Test JSON serialization
    pricing_dict = pricing.to_dict()
    if "cost_per_serving" in pricing_dict and pricing_dict["cost_per_serving"] == 3.5:
        print(f"✓ Pricing serializes to JSON correctly")
    else:
        print(f"✗ Pricing JSON serialization failed")
        return False
    
    return True


def test_recipe_macro_alignment():
    """Test macro alignment scoring."""
    print("\n=== Testing Macro Alignment Scoring ===")
    
    target_macros = {
        "protein_g": 200,
        "carbs_g": 250,
        "fats_g": 80
    }
    
    # Perfect match
    recipe_perfect = Recipe(
        id=1,
        title="Perfect Meal",
        image="test.jpg",
        used_ingredients=["chicken"],
        missed_ingredients=[],
        macronutrients=RecipeNutrition(
            calories=2000,
            protein_g=200,
            carbs_g=250,
            fats_g=80
        )
    )
    
    score_perfect = recipe_perfect.calculate_macro_alignment(target_macros)
    if score_perfect >= 95:
        print(f"✓ Perfect macro match scores high: {score_perfect}/100")
    else:
        print(f"✗ Perfect macro match should score >95, got {score_perfect}")
        return False
    
    # Poor match
    recipe_poor = Recipe(
        id=2,
        title="Poor Match",
        image="test.jpg",
        used_ingredients=["cake"],
        missed_ingredients=[],
        macronutrients=RecipeNutrition(
            calories=2000,
            protein_g=10,
            carbs_g=500,
            fats_g=50
        )
    )
    
    score_poor = recipe_poor.calculate_macro_alignment(target_macros)
    if score_poor < 50:
        print(f"✓ Poor macro match scores low: {score_poor}/100")
    else:
        print(f"✗ Poor macro match should score <50, got {score_poor}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("RECIPE BACKEND - LOCAL TESTING SUITE")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_user_input_validation()
    all_passed &= test_user_metrics()
    all_passed &= test_recipe_nutrition()
    all_passed &= test_recipe_pricing()
    all_passed &= test_recipe_macro_alignment()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Backend is ready!")
    else:
        print("✗ SOME TESTS FAILED - Fix errors before deployment")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
