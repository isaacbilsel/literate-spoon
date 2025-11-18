"""
Integration tests for Literate Spoon API endpoints.
Simplified version using app test client directly.
"""

import pytest
import json
import os
import tempfile
from app_models import Base, engine, init_db, SessionLocal
from main import app, create_access_token


@pytest.fixture(scope="session")
def test_app():
    """Setup Flask app for testing."""
    app.config["TESTING"] = True
    
    # Create tables
    with app.app_context():
        Base.metadata.create_all(bind=engine)
    
    yield app
    
    # Cleanup
    with app.app_context():
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()


@pytest.fixture
def test_user(test_app):
    """Create a test user and return email + password."""
    from app_models import User, Profile
    
    with test_app.app_context():
        db = SessionLocal()
        
        # Check if user already exists
        user = db.query(User).filter(User.email == "test@example.com").first()
        if not user:
            user = User(
                email="test@example.com",
                password_hash=User.hash_password("password123"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            profile = Profile(
                user_id=user.id,
                first_name="Test",
                gender="M",
                zip_code="12345",
            )
            db.add(profile)
            db.commit()
        
        user_id = user.id
        db.close()
    
    return {
        "id": user_id,
        "email": "test@example.com",
        "password": "password123",
    }


@pytest.fixture
def auth_token(test_app, test_user):
    """Get auth token for test user."""
    with test_app.app_context():
        return create_access_token(test_user["id"], "user")


# ============ AUTHENTICATION TESTS ============
class TestAuth:
    """Authentication endpoint tests."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "secure123",
                "firstName": "John",
                "gender": "M",
                "zipCode": "90210",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["email"] == "newuser@test.com"
        assert "accessToken" in data

    def test_register_missing_password(self, client):
        """Test registration without password."""
        response = client.post(
            "/api/auth/register",
            json={"email": "another@test.com"},
        )
        assert response.status_code == 400

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["email"] == test_user["email"]
        assert "accessToken" in data

    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": test_user["email"],
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_get_current_user(self, client, auth_token):
        """Test getting current user info."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_logout(self, client, auth_token):
        """Test logout."""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

    def test_refresh_token(self, client, auth_token):
        """Test token refresh."""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "accessToken" in data


# ============ PROFILE TESTS ============
class TestProfile:
    """Profile endpoint tests."""

    def test_get_profile(self, client, auth_token):
        """Test getting user profile."""
        response = client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["firstName"] == "Test"

    def test_get_profile_no_token(self, client):
        """Test getting profile without token."""
        response = client.get("/api/profile")
        assert response.status_code == 401

    def test_update_profile(self, client, auth_token):
        """Test updating profile."""
        response = client.put(
            "/api/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "firstName": "Updated",
                "gender": "F",
                "bio": "New bio",
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["profile"]["firstName"] == "Updated"
        assert data["profile"]["bio"] == "New bio"

    def test_patch_profile(self, client, auth_token):
        """Test patching profile."""
        response = client.patch(
            "/api/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"zipCode": "99999"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["profile"]["zipCode"] == "99999"


# ============ MEAL PLAN TESTS ============
class TestMealPlan:
    """Meal plan endpoint tests."""

    def test_list_meal_plans(self, client, auth_token):
        """Test listing meal plans."""
        response = client.get(
            "/api/meal-plans",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "meal_plans" in data

    def test_create_meal_plan(self, client, auth_token):
        """Test creating a meal plan."""
        response = client.post(
            "/api/meal-plans",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Weekly Plan",
                "description": "Healthy meals",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["meal_plan"]["name"] == "Weekly Plan"

    def test_get_meal_plan(self, client, auth_token):
        """Test getting a meal plan."""
        # First create one
        create_response = client.post(
            "/api/meal-plans",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "Test Plan"},
        )
        meal_plan_id = create_response.get_json()["meal_plan"]["id"]
        
        # Then get it
        response = client.get(
            f"/api/meal-plans/{meal_plan_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Test Plan"

    def test_update_meal_plan(self, client, auth_token):
        """Test updating a meal plan."""
        # Create
        create_response = client.post(
            "/api/meal-plans",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "Original"},
        )
        meal_plan_id = create_response.get_json()["meal_plan"]["id"]
        
        # Update
        response = client.put(
            f"/api/meal-plans/{meal_plan_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "Updated"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["meal_plan"]["name"] == "Updated"

    def test_activate_meal_plan(self, client, auth_token):
        """Test activating a meal plan."""
        # Create
        create_response = client.post(
            "/api/meal-plans",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "Plan to Activate"},
        )
        meal_plan_id = create_response.get_json()["meal_plan"]["id"]
        
        # Activate
        response = client.post(
            f"/api/meal-plans/{meal_plan_id}/activate",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["meal_plan"]["isActive"] is True


# ============ GROCERY LIST TESTS ============
class TestGroceryList:
    """Grocery list endpoint tests."""

    def test_list_grocery_lists(self, client, auth_token):
        """Test listing grocery lists."""
        response = client.get(
            "/api/grocery-lists",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "grocery_lists" in data

    def test_create_grocery_list(self, client, auth_token):
        """Test creating a grocery list."""
        response = client.post(
            "/api/grocery-lists",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"items": '["milk", "eggs"]'},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["grocery_list"]["items"] == '["milk", "eggs"]'

    def test_get_grocery_list(self, client, auth_token):
        """Test getting a grocery list."""
        # Create
        create_response = client.post(
            "/api/grocery-lists",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"items": '["bread"]'},
        )
        gl_id = create_response.get_json()["grocery_list"]["id"]
        
        # Get
        response = client.get(
            f"/api/grocery-lists/{gl_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["items"] == '["bread"]'

    def test_update_grocery_list(self, client, auth_token):
        """Test updating a grocery list."""
        # Create
        create_response = client.post(
            "/api/grocery-lists",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"items": '["apple"]'},
        )
        gl_id = create_response.get_json()["grocery_list"]["id"]
        
        # Update
        response = client.put(
            f"/api/grocery-lists/{gl_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"items": '["apple", "banana"]'},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "banana" in data["grocery_list"]["items"]


# ============ CHAT TESTS ============
class TestChat:
    """Chat endpoint tests."""

    def test_parse_chat(self, client, auth_token):
        """Test parsing chat message."""
        response = client.post(
            "/api/chat/parse",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"message": "I want vegetarian meals"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "I want vegetarian meals"
        assert "response" in data

    def test_parse_chat_no_token(self, client):
        """Test parsing chat without token."""
        response = client.post(
            "/api/chat/parse",
            json={"message": "Hello"},
        )
        assert response.status_code == 401

    def test_parse_chat_empty_message(self, client, auth_token):
        """Test parsing empty message."""
        response = client.post(
            "/api/chat/parse",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"message": ""},
        )
        assert response.status_code == 400

    def test_get_chat_history(self, client, auth_token):
        """Test getting chat history."""
        response = client.get(
            "/api/chat/history",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "chat_history" in data


# ============ UTILITY TESTS ============
class TestUtility:
    """Utility endpoint tests."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data

    def test_404_error(self, client):
        """Test 404 handling."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_cors_preflight(self, client):
        """Test CORS preflight."""
        response = client.options("/api/recipes")
        assert response.status_code in [200, 405]  # 200 if handled, 405 if not


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
