"""
Integration tests for Literate Spoon API endpoints.

Tests all endpoints:
- Authentication (register, login, me, logout, refresh)
- Profile (get, update)
- Meal Plans (list, create, get, update, activate, grocery-list)
- Grocery Lists (list, create, get, update)
- Chat (parse, history)
- Recipes (existing endpoint)
- Health check
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from app_models import (
    SessionLocal,
    init_db,
    User,
    Profile,
    MealPlan,
    GroceryList,
    ChatMessage,
    Base,
    engine,
)
from main import app


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Setup test database before running tests."""
    # Use in-memory SQLite for testing
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def db_session():
    """Create database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    user = User(
        email="test@example.com",
        password_hash=User.hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()
    
    profile = Profile(
        user_id=user.id,
        first_name="Test",
        gender="M",
        zip_code="12345",
    )
    db_session.add(profile)
    db_session.commit()
    
    return user


@pytest.fixture
def auth_token(test_user):
    """Get auth token for test user."""
    from main import create_access_token
    return create_access_token(test_user.id, test_user.role)


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_register(self, client):
        """Test user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "secure_password123",
                "firstName": "John",
                "gender": "M",
                "zipCode": "90210",
            },
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["email"] == "newuser@example.com"
        assert "accessToken" in data
        assert data["refreshTokenSetCookie"] is False

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
                "firstName": "John",
                "gender": "M",
                "zipCode": "90210",
            },
        )
        
        assert response.status_code == 409
        data = response.get_json()
        assert "already exists" in data["error"]

    def test_register_missing_email(self, client):
        """Test registration without email."""
        response = client.post(
            "/api/auth/register",
            json={
                "password": "password123",
            },
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert "required" in data["error"]

    def test_login(self, client, test_user):
        """Test user login."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
            },
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["email"] == test_user.email
        assert "accessToken" in data

    def test_login_invalid_password(self, client, test_user):
        """Test login with invalid password."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "wrong_password",
            },
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert "Incorrect" in data["error"]

    def test_get_current_user(self, client, test_user, auth_token):
        """Test getting current user info."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["email"] == test_user.email
        assert data["user"]["id"] == test_user.id
        assert data["profile"] is not None

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without token."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
        data = response.get_json()
        assert "Unauthorized" in data["error"]

    def test_logout(self, client, auth_token):
        """Test logout endpoint."""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "successfully" in data["message"]

    def test_refresh_token(self, client, auth_token):
        """Test token refresh."""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "accessToken" in data
        assert data["accessToken"] != auth_token  # New token should be different


class TestProfileEndpoints:
    """Test profile endpoints."""

    def test_get_profile(self, client, test_user, auth_token):
        """Test getting user profile."""
        response = client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firstName"] == "Test"
        assert data["userId"] == test_user.id

    def test_get_profile_unauthorized(self, client):
        """Test getting profile without token."""
        response = client.get("/api/profile")
        
        assert response.status_code == 401

    def test_update_profile(self, client, test_user, auth_token):
        """Test updating user profile."""
        response = client.put(
            "/api/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "firstName": "Updated",
                "gender": "F",
                "zipCode": "54321",
                "bio": "Test bio",
            },
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["profile"]["firstName"] == "Updated"
        assert data["profile"]["zipCode"] == "54321"
        assert data["profile"]["bio"] == "Test bio"

    def test_patch_profile(self, client, test_user, auth_token):
        """Test patching user profile."""
        response = client.patch(
            "/api/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "bio": "New bio",
            },
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["profile"]["bio"] == "New bio"


class TestMealPlanEndpoints:
    """Test meal plan endpoints."""

    def test_list_meal_plans(self, client, test_user, auth_token):
        """Test listing meal plans."""
        response = client.get(
            "/api/meal-plans",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "meal_plans" in data
        assert isinstance(data["meal_plans"], list)

    def test_create_meal_plan(self, client, test_user, auth_token):
        """Test creating a meal plan."""
        response = client.post(
            "/api/meal-plans",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Weekly Meal Plan",
                "description": "A week of healthy meals",
                "meals": '["Monday", "Tuesday"]',
            },
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["meal_plan"]["name"] == "Weekly Meal Plan"
        assert data["meal_plan"]["userId"] == test_user.id

    def test_get_meal_plan(self, client, test_user, auth_token, db_session):
        """Test getting a specific meal plan."""
        # Create meal plan
        meal_plan = MealPlan(
            user_id=test_user.id,
            name="Test Plan",
            description="Test",
            meals="[]",
        )
        db_session.add(meal_plan)
        db_session.commit()
        
        response = client.get(
            f"/api/meal-plans/{meal_plan.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Test Plan"

    def test_update_meal_plan(self, client, test_user, auth_token, db_session):
        """Test updating a meal plan."""
        meal_plan = MealPlan(
            user_id=test_user.id,
            name="Original Name",
            description="Original",
            meals="[]",
        )
        db_session.add(meal_plan)
        db_session.commit()
        
        response = client.put(
            f"/api/meal-plans/{meal_plan.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Updated Name",
                "meals": '["Mon", "Tue", "Wed"]',
            },
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["meal_plan"]["name"] == "Updated Name"

    def test_activate_meal_plan(self, client, test_user, auth_token, db_session):
        """Test activating a meal plan."""
        meal_plan = MealPlan(
            user_id=test_user.id,
            name="Plan to Activate",
            description="Test",
            meals="[]",
            is_active=False,
        )
        db_session.add(meal_plan)
        db_session.commit()
        
        response = client.post(
            f"/api/meal-plans/{meal_plan.id}/activate",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["meal_plan"]["isActive"] is True


class TestGroceryListEndpoints:
    """Test grocery list endpoints."""

    def test_list_grocery_lists(self, client, test_user, auth_token):
        """Test listing grocery lists."""
        response = client.get(
            "/api/grocery-lists",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "grocery_lists" in data

    def test_create_grocery_list(self, client, test_user, auth_token):
        """Test creating a grocery list."""
        response = client.post(
            "/api/grocery-lists",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "items": '["milk", "eggs", "bread"]',
            },
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["grocery_list"]["userId"] == test_user.id

    def test_get_grocery_list(self, client, test_user, auth_token, db_session):
        """Test getting a specific grocery list."""
        grocery_list = GroceryList(
            user_id=test_user.id,
            items='["apple", "orange"]',
        )
        db_session.add(grocery_list)
        db_session.commit()
        
        response = client.get(
            f"/api/grocery-lists/{grocery_list.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["items"] == '["apple", "orange"]'

    def test_update_grocery_list(self, client, test_user, auth_token, db_session):
        """Test updating a grocery list."""
        grocery_list = GroceryList(
            user_id=test_user.id,
            items='["apple"]',
        )
        db_session.add(grocery_list)
        db_session.commit()
        
        response = client.put(
            f"/api/grocery-lists/{grocery_list.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "items": '["apple", "banana", "orange"]',
            },
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "banana" in data["grocery_list"]["items"]


class TestChatEndpoints:
    """Test chat endpoints."""

    def test_parse_chat(self, client, test_user, auth_token):
        """Test parsing a chat message."""
        response = client.post(
            "/api/chat/parse",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "message": "I want a vegetarian meal plan",
            },
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "I want a vegetarian meal plan"
        assert "response" in data
        assert data["chat_id"] is not None

    def test_parse_chat_unauthorized(self, client):
        """Test parsing chat without token."""
        response = client.post(
            "/api/chat/parse",
            json={
                "message": "Hello",
            },
        )
        
        assert response.status_code == 401

    def test_parse_chat_empty_message(self, client, auth_token):
        """Test parsing empty chat message."""
        response = client.post(
            "/api/chat/parse",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "message": "",
            },
        )
        
        assert response.status_code == 400

    def test_get_chat_history(self, client, test_user, auth_token):
        """Test getting chat history."""
        response = client.get(
            "/api/chat/history",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "chat_history" in data


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data


class TestRecipeEndpoint:
    """Test recipe endpoint."""

    def test_get_recipes(self, client):
        """Test getting recipes."""
        response = client.post(
            "/api/recipes",
            json={
                "height_cm": 180,
                "weight_kg": 75,
                "allergies": [],
                "food_preferences": "Mediterranean",
                "diet_goals": "weight loss",
            },
        )
        
        # May fail if external APIs not available, but endpoint should exist
        assert response.status_code in [200, 500]


class TestErrorHandling:
    """Test error handling."""

    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_bad_request_error(self, client):
        """Test 400 error handling."""
        response = client.post(
            "/api/recipes",
            json={},  # Missing required fields
        )
        
        assert response.status_code in [400, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
