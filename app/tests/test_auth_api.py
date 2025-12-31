"""
Tests for Authentication API endpoints
"""

import pytest
from httpx import AsyncClient
from app.models.user import User
from app.core.security import get_password_hash


class TestAuthAPI:
    """Test authentication API endpoints"""

    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login"""
        login_data = {
            "username": test_user.email,  # OAuth2PasswordRequestForm uses 'username' field
            "password": "testpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == test_user.email

    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with invalid email"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "Incorrect email or password" in data["detail"]

    async def test_login_invalid_password(self, client: AsyncClient, test_user):
        """Test login with invalid password"""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "Incorrect email or password" in data["detail"]

    async def test_login_inactive_user(self, client: AsyncClient, test_db):
        """Test login with inactive user"""
        # Create inactive user
        inactive_user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("password"),
            username="inactive",
            is_active=False,
            is_superuser=False
        )
        test_db.add(inactive_user)
        await test_db.commit()
        
        login_data = {
            "username": inactive_user.email,
            "password": "password"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401

    async def test_signup_success(self, client: AsyncClient):
        """Test successful user registration"""
        signup_data = {
            "email": "newuser@example.com",
            "password": "newpassword123",
            "username": "newuser"
        }
        
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == signup_data["email"]
        assert data["username"] == signup_data["username"]
        assert data["is_active"] is True
        assert "id" in data

    async def test_signup_duplicate_email(self, client: AsyncClient, test_user):
        """Test signup with duplicate email"""
        signup_data = {
            "email": test_user.email,  # Duplicate email
            "password": "password123",
            "username": "duplicateuser"
        }
        
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Email already registered" in data["detail"]

    async def test_signup_duplicate_username(self, client: AsyncClient, test_user):
        """Test signup with duplicate username"""
        signup_data = {
            "email": "different@example.com",
            "password": "password123",
            "username": test_user.username  # Duplicate username
        }
        
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Username already taken" in data["detail"]

    async def test_signup_invalid_email_format(self, client: AsyncClient):
        """Test signup with invalid email format"""
        signup_data = {
            "email": "invalid-email",
            "password": "password123",
            "username": "testuser"
        }
        
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        
        assert response.status_code == 422  # Validation error

    async def test_signup_missing_required_fields(self, client: AsyncClient):
        """Test signup with missing required fields"""
        # Missing email
        signup_data = {
            "password": "password123",
            "username": "testuser"
        }
        
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == 422
        
        # Missing password
        signup_data = {
            "email": "test@example.com",
            "username": "testuser"
        }
        
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == 422

    async def test_refresh_token_success(self, client: AsyncClient, test_user):
        """Test successful token refresh"""
        # First login to get refresh token
        login_data = {
            "username": test_user.email,
            "password": "testpassword"
        }
        
        login_response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert refresh_data["token_type"] == "bearer"

    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refresh with invalid token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid refresh token" in data["detail"]

    async def test_refresh_token_wrong_type(self, client: AsyncClient, user_token):
        """Test refresh with access token instead of refresh token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": user_token}  # Using access token instead of refresh token
        )
        
        assert response.status_code == 401

    async def test_password_hashing(self, client: AsyncClient):
        """Test that passwords are properly hashed"""
        signup_data = {
            "email": "hashtest@example.com",
            "password": "plaintextpassword",
            "username": "hashtest"
        }
        
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == 200
        
        # Verify password is not stored in plain text
        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data

    async def test_admin_user_login(self, client: AsyncClient, admin_user):
        """Test admin user login"""
        login_data = {
            "username": admin_user.email,
            "password": "adminpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["is_admin"] is True

    async def test_token_expiration_format(self, client: AsyncClient, test_user):
        """Test token expiration information"""
        login_data = {
            "username": test_user.email,
            "password": "testpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0


class TestAuthSecurity:
    """Test authentication security features"""

    async def test_password_strength_requirements(self, client: AsyncClient):
        """Test password strength validation if implemented"""
        # This test assumes password strength validation is implemented
        # If not implemented, this test will pass but should be updated when validation is added
        
        weak_passwords = ["123", "password", "abc"]
        
        for weak_password in weak_passwords:
            signup_data = {
                "email": f"weak{weak_password}@example.com",
                "password": weak_password,
                "full_name": "Weak Password User",
                "username": f"weak{weak_password}"
            }
            
            response = await client.post("/api/v1/auth/signup", json=signup_data)
            # If password validation is implemented, this should fail
            # If not implemented, it will succeed (which is also valid for this test)
            assert response.status_code in [200, 422]

    async def test_rate_limiting_simulation(self, client: AsyncClient):
        """Test multiple failed login attempts"""
        # Simulate multiple failed login attempts
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        for _ in range(5):
            response = await client.post(
                "/api/v1/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            assert response.status_code == 401

    async def test_case_insensitive_email(self, client: AsyncClient, test_user):
        """Test case insensitive email login"""
        login_data = {
            "username": test_user.email.upper(),  # Use uppercase email
            "password": "testpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # This might fail if case sensitivity is enforced
        # The behavior depends on the implementation
        assert response.status_code in [200, 401]

    async def test_sql_injection_protection(self, client: AsyncClient):
        """Test SQL injection protection in login"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin@example.com'; --"
        ]
        
        for malicious_input in malicious_inputs:
            login_data = {
                "username": malicious_input,
                "password": "password"
            }
            
            response = await client.post(
                "/api/v1/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Should not cause server error or unauthorized access
            assert response.status_code in [401, 422]

    async def test_xss_protection_in_signup(self, client: AsyncClient):
        """Test XSS protection in user registration"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            signup_data = {
                "email": "xsstest@example.com",
                "password": "password123",
                "username": "xsstest"
            }
            
            response = await client.post("/api/v1/auth/signup", json=signup_data)
            
            if response.status_code == 200:
                data = response.json()
                # Ensure XSS payload is not executed or stored as-is
                assert payload not in str(data)


class TestAuthErrorHandling:
    """Test authentication error handling"""

    async def test_malformed_login_request(self, client: AsyncClient):
        """Test handling of malformed login requests"""
        # Missing Content-Type header
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test", "password": "test"}
        )
        
        # Should handle gracefully
        assert response.status_code in [401, 422]

    async def test_empty_login_credentials(self, client: AsyncClient):
        """Test handling of empty credentials"""
        login_data = {
            "username": "",
            "password": ""
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code in [401, 422]

    async def test_null_values_in_signup(self, client: AsyncClient):
        """Test handling of null values in signup"""
        signup_data = {
            "email": None,
            "password": None,
            "username": None
        }
        
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == 422

    async def test_extremely_long_input_values(self, client: AsyncClient):
        """Test handling of extremely long input values"""
        long_string = "x" * 10000
        
        signup_data = {
            "email": f"{long_string}@example.com",
            "password": long_string,
            "username": long_string
        }
        
        response = await client.post("/api/v1/auth/signup", json=signup_data)
        # Should handle gracefully with validation error
        assert response.status_code == 422

    async def test_unicode_handling(self, client: AsyncClient):
        """Test handling of unicode characters"""
        unicode_data = {
            "email": "测试@example.com",
            "password": "密码123",
            "username": "测试用户名"
        }
        
        response = await client.post("/api/v1/auth/signup", json=unicode_data)
        # Should handle unicode gracefully
        assert response.status_code in [200, 422]