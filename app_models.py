"""
Data models and validation for the recipe recommendation system.
Handles all input validation and data transformation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import re
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
import bcrypt

Base = declarative_base()

# SQLite setup for local dev
engine = create_engine('sqlite:///literate_spoon.db', echo=False)
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    role = Column(String(32), default='user')
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    profile = relationship('Profile', uselist=False, back_populates='user')

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

class Profile(Base):
    __tablename__ = 'profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    first_name = Column(String(100))
    gender = Column(String(32))
    zip_code = Column(String(16))
    weight_kg = Column(String(16))
    height_cm = Column(String(16))
    age = Column(Integer)
    dietary_restrictions = Column(Text)
    budget_constraints = Column(Text)
    diet_health_goals = Column(Text)
    bio = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship('User', back_populates='profile')

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "firstName": self.first_name,
            "gender": self.gender,
            "zipCode": self.zip_code,
            "weightKg": self.weight_kg,
            "heightCm": self.height_cm,
            "age": self.age,
            "dietaryRestrictions": self.dietary_restrictions,
            "budgetConstraints": self.budget_constraints,
            "dietHealthGoals": self.diet_health_goals,
            "bio": self.bio,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class MealPlan(Base):
    __tablename__ = 'meal_plans'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    meals = Column(Text)  # JSON array of meal data
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship('User')

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "name": self.name,
            "description": self.description,
            "meals": self.meals,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class GroceryList(Base):
    __tablename__ = 'grocery_lists'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    meal_plan_id = Column(Integer, ForeignKey('meal_plans.id'), nullable=True)
    items = Column(Text)  # JSON array of items
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship('User')
    meal_plan = relationship('MealPlan')

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "mealPlanId": self.meal_plan_id,
            "items": self.items,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship('User')

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "message": self.message,
            "response": self.response,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


def init_db():
    Base.metadata.create_all(bind=engine)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


@dataclass
class UserInput:
    """Validated user input from frontend."""
    height_cm: int
    weight_kg: int
    allergies: List[str]
    food_preferences: str
    diet_goals: str

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "UserInput":
        """
        Create UserInput from dictionary with full validation.
        
        Args:
            data: Dictionary from JSON request
            
        Returns:
            UserInput object with validated fields
            
        Raises:
            ValidationError: If any field fails validation
        """
        # Validate height
        try:
            height_cm = int(data.get("height_cm", 0))
        except (TypeError, ValueError):
            raise ValidationError("height_cm must be an integer", "height_cm")
        
        if not (100 <= height_cm <= 250):
            raise ValidationError("height_cm must be between 100-250 cm", "height_cm")
        
        # Validate weight
        try:
            weight_kg = int(data.get("weight_kg", 0))
        except (TypeError, ValueError):
            raise ValidationError("weight_kg must be an integer", "weight_kg")
        
        if not (30 <= weight_kg <= 300):
            raise ValidationError("weight_kg must be between 30-300 kg", "weight_kg")
        
        # Validate allergies
        allergies_raw = data.get("allergies", [])
        if not isinstance(allergies_raw, list):
            raise ValidationError("allergies must be an array", "allergies")
        
        if len(allergies_raw) > 10:
            raise ValidationError("allergies must contain at most 10 items", "allergies")
        
        # Normalize allergies: lowercase, trim, remove empty
        allergies = [
            str(allergy).strip().lower()
            for allergy in allergies_raw
            if str(allergy).strip()
        ]
        
        # Validate no special characters in allergies
        for allergy in allergies:
            if not re.match(r"^[a-z0-9\s\-]+$", allergy):
                raise ValidationError(
                    f"Invalid allergy '{allergy}': only alphanumeric, spaces, and hyphens allowed",
                    "allergies"
                )
        
        # Validate food_preferences
        food_preferences = str(data.get("food_preferences", "")).strip()
        if not (1 <= len(food_preferences) <= 500):
            raise ValidationError(
                "food_preferences must be 1-500 characters",
                "food_preferences"
            )
        
        # Validate diet_goals
        diet_goals = str(data.get("diet_goals", "")).strip()
        if not (1 <= len(diet_goals) <= 500):
            raise ValidationError(
                "diet_goals must be 1-500 characters",
                "diet_goals"
            )
        
        return UserInput(
            height_cm=height_cm,
            weight_kg=weight_kg,
            allergies=allergies,
            food_preferences=food_preferences,
            diet_goals=diet_goals
        )


@dataclass
class UserMetrics:
    """Calculated health metrics for the user."""
    height_cm: int
    weight_kg: int
    bmi: float
    tdee_estimate: int
    macro_targets: Dict[str, int]
    
    @staticmethod
    def calculate(user_input: UserInput) -> "UserMetrics":
        """
        Calculate user metrics from input data.
        
        Args:
            user_input: Validated user input
            
        Returns:
            UserMetrics with calculated values
        """
        height_m = user_input.height_cm / 100
        bmi = user_input.weight_kg / (height_m ** 2)
        
        # Estimate BMR using Mifflin-St Jeor equation
        # Assumes average person (approximation)
        # More accurate with age/gender, but using conservative estimate
        bmr = 10 * user_input.weight_kg + 6.25 * user_input.height_cm - 5
        
        # Activity factor: assuming moderate activity (1.5x)
        # Can be adjusted based on diet_goals
        activity_factor = 1.5
        tdee = int(bmr * activity_factor)
        
        # Adjust macro targets based on diet goals
        if "weight loss" in user_input.diet_goals.lower():
            # High protein for weight loss: 30% protein, 40% carbs, 30% fats
            macro_targets = {
                "protein_g": int((tdee * 0.30) / 4),
                "carbs_g": int((tdee * 0.40) / 4),
                "fats_g": int((tdee * 0.30) / 9)
            }
        elif "muscle" in user_input.diet_goals.lower() or "gain" in user_input.diet_goals.lower():
            # Muscle gain: 35% protein, 45% carbs, 20% fats
            macro_targets = {
                "protein_g": int((tdee * 0.35) / 4),
                "carbs_g": int((tdee * 0.45) / 4),
                "fats_g": int((tdee * 0.20) / 9)
            }
        else:
            # Balanced: 30% protein, 40% carbs, 30% fats
            macro_targets = {
                "protein_g": int((tdee * 0.30) / 4),
                "carbs_g": int((tdee * 0.40) / 4),
                "fats_g": int((tdee * 0.30) / 9)
            }
        
        return UserMetrics(
            height_cm=user_input.height_cm,
            weight_kg=user_input.weight_kg,
            bmi=round(bmi, 1),
            tdee_estimate=tdee,
            macro_targets=macro_targets
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "bmi": self.bmi,
            "tdee_estimate": self.tdee_estimate,
            "macro_targets": self.macro_targets
        }


@dataclass
class RecipeNutrition:
    """Nutritional information for a recipe."""
    calories: int
    protein_g: float
    carbs_g: float
    fats_g: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "calories": self.calories,
            "protein_g": round(self.protein_g, 1),
            "carbs_g": round(self.carbs_g, 1),
            "fats_g": round(self.fats_g, 1)
        }
    
    @staticmethod
    def from_spoonacular(nutrition_data: Dict[str, Any]) -> Optional["RecipeNutrition"]:
        """
        Extract nutrition from Spoonacular API response.
        
        Args:
            nutrition_data: Raw data from Spoonacular nutrition endpoint
            
        Returns:
            RecipeNutrition object or None if data is incomplete
        """
        try:
            # Spoonacular returns nutrients as array of objects
            nutrients = {n["name"]: n["amount"] for n in nutrition_data.get("nutrients", [])}
            
            return RecipeNutrition(
                calories=int(nutrients.get("Calories", 0)),
                protein_g=float(nutrients.get("Protein", 0)),
                carbs_g=float(nutrients.get("Carbohydrates", 0)),
                fats_g=float(nutrients.get("Fat", 0))
            )
        except (KeyError, TypeError, ValueError):
            return None


@dataclass
class RecipePricing:
    """Pricing information for a recipe."""
    cost_per_serving: float
    currency: str = "USD"
    servings: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "cost_per_serving": round(self.cost_per_serving, 2),
            "currency": self.currency,
            "servings": self.servings
        }
    
    @staticmethod
    def from_spoonacular(price_data: Dict[str, Any], servings: int = 1) -> Optional["RecipePricing"]:
        """
        Extract pricing from Spoonacular API response.
        
        Args:
            price_data: Raw data from Spoonacular price breakdown endpoint
            servings: Number of servings
            
        Returns:
            RecipePricing object or None if data is incomplete
        """
        try:
            total_cost = float(price_data.get("totalCost", 0))
            cost_per_serving = total_cost / servings if servings > 0 else 0
            
            return RecipePricing(
                cost_per_serving=cost_per_serving / 100,  # Spoonacular returns cents
                servings=servings
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return None


@dataclass
class Recipe:
    """Complete recipe with all enriched data."""
    id: int
    title: str
    image: str
    used_ingredients: List[str]
    missed_ingredients: List[str]
    macronutrients: Optional[RecipeNutrition] = None
    pricing: Optional[RecipePricing] = None
    macro_alignment_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "id": self.id,
            "title": self.title,
            "image": self.image,
            "used_ingredients": self.used_ingredients,
            "missed_ingredients": self.missed_ingredients,
            "macronutrients": self.macronutrients.to_dict() if self.macronutrients else None,
            "pricing": self.pricing.to_dict() if self.pricing else None
        }
    
    def calculate_macro_alignment(self, target_macros: Dict[str, int]) -> float:
        """
        Calculate how well recipe macros align with user targets.
        Returns score 0-100 (100 = perfect alignment).
        
        Args:
            target_macros: Target macro amounts {protein_g, carbs_g, fats_g}
            
        Returns:
            Alignment score 0-100
        """
        if not self.macronutrients:
            return 0.0
        
        # Calculate deviation from targets
        protein_dev = abs(self.macronutrients.protein_g - target_macros.get("protein_g", 0)) / max(target_macros.get("protein_g", 1), 1)
        carbs_dev = abs(self.macronutrients.carbs_g - target_macros.get("carbs_g", 0)) / max(target_macros.get("carbs_g", 1), 1)
        fats_dev = abs(self.macronutrients.fats_g - target_macros.get("fats_g", 0)) / max(target_macros.get("fats_g", 1), 1)
        
        # Average deviation (0 = perfect, 1+ = poor)
        avg_dev = (protein_dev + carbs_dev + fats_dev) / 3
        
        # Convert to 0-100 score
        score = max(0, 100 - (avg_dev * 100))
        return round(score, 1)


class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ExternalAPIError(APIError):
    """Exception for external API (Gemini, Spoonacular) failures."""
    pass
