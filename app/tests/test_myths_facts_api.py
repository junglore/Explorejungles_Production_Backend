"""
Comprehensive tests for Myths vs Facts API endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4, UUID
from unittest.mock import patch, AsyncMock
import tempfile
import os
from pathlib import Path

from app.models.myth_fact import MythFact
from app.models.category import Category
from app.models.user import User
from app.schemas.myth_fact import MythFactCreate, MythFactUpdate


class TestMythsFactsAPI:
    """Test class for Myths vs Facts API endpoints"""

    @pytest.mark.asyncio
    async def test_get_myths_facts_list(self, client: AsyncClient, test_myth_fact: MythFact):
        """Test getting paginated list of myths vs facts"""
        response = await client.get("/api/v1/myths-facts/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) >= 1
        
        # Check pagination structure
        pagination = data["pagination"]
        assert "page" in pagination
        assert "limit" in pagination
        assert "total" in pagination
        assert "pages" in pagination
        
        # Check item structure
        item = data["items"][0]
        assert "id" in item
        assert "title" in item
        assert "myth_statement" in item
        assert "fact_explanation" in item
        assert "category" in item
        assert "image_url" in item
        assert "created_at" in item
        assert "is_featured" in item

    @pytest.mark.asyncio
    async def test_get_myths_facts_with_pagination(self, client: AsyncClient, test_db: AsyncSession, test_category: Category):
        """Test pagination parameters"""
        # Create multiple myth facts
        for i in range(15):
            myth_fact = MythFact(
                title=f"Test Myth {i}",
                myth_content=f"Myth content {i}",
                fact_content=f"Fact content {i}",
                category_id=test_category.id
            )
            test_db.add(myth_fact)
        await test_db.commit()
        
        # Test first page
        response = await client.get("/api/v1/myths-facts/?page=1&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 5
        
        # Test second page
        response = await client.get("/api/v1/myths-facts/?page=2&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["pagination"]["page"] == 2

    @pytest.mark.asyncio
    async def test_get_myths_facts_featured_filter(self, client: AsyncClient, test_myth_fact: MythFact, featured_myth_fact: MythFact):
        """Test filtering by featured status"""
        # Get all items
        response = await client.get("/api/v1/myths-facts/")
        all_data = response.json()
        assert len(all_data["items"]) >= 2
        
        # Get only featured items
        response = await client.get("/api/v1/myths-facts/?featured_only=true")
        assert response.status_code == 200
        featured_data = response.json()
        
        # Should have fewer items
        assert len(featured_data["items"]) < len(all_data["items"])
        
        # All returned items should be featured
        for item in featured_data["items"]:
            assert item["is_featured"] is True

    @pytest.mark.asyncio
    async def test_get_myths_facts_category_filter(self, client: AsyncClient, test_db: AsyncSession):
        """Test filtering by category"""
        # Create two categories
        category1 = Category(name="Category 1", slug="category-1")
        category2 = Category(name="Category 2", slug="category-2")
        test_db.add_all([category1, category2])
        await test_db.commit()
        await test_db.refresh(category1)
        await test_db.refresh(category2)
        
        # Create myth facts in different categories
        myth1 = MythFact(
            title="Myth in Category 1",
            myth_content="Myth 1",
            fact_content="Fact 1",
            category_id=category1.id
        )
        myth2 = MythFact(
            title="Myth in Category 2",
            myth_content="Myth 2",
            fact_content="Fact 2",
            category_id=category2.id
        )
        test_db.add_all([myth1, myth2])
        await test_db.commit()
        
        # Filter by category 1
        response = await client.get(f"/api/v1/myths-facts/?category_id={category1.id}")
        assert response.status_code == 200
        data = response.json()
        
        # Should only return items from category 1
        for item in data["items"]:
            assert item["category"] == "Category 1"

    @pytest.mark.asyncio
    async def test_create_myth_fact_success(self, client: AsyncClient, admin_headers: dict, test_category: Category):
        """Test successful creation of myth vs fact"""
        myth_data = {
            "title": "New Myth vs Fact",
            "myth_content": "This is a new myth",
            "fact_content": "This is the corresponding fact",
            "category_id": str(test_category.id),
            "is_featured": True,
            "image_url": "/new/image.jpg"
        }
        
        response = await client.post(
            "/api/v1/myths-facts/",
            json=myth_data,
            headers=admin_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Myth vs fact entry created successfully"
        assert "data" in data
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_create_myth_fact_unauthorized(self, client: AsyncClient, auth_headers: dict):
        """Test creation fails for non-admin users"""
        myth_data = {
            "title": "Unauthorized Myth",
            "myth_content": "This should fail",
            "fact_content": "Because user is not admin"
        }
        
        response = await client.post(
            "/api/v1/myths-facts/",
            json=myth_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "Only administrators can create" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_myth_fact_no_auth(self, client: AsyncClient):
        """Test creation fails without authentication"""
        myth_data = {
            "title": "No Auth Myth",
            "myth_content": "This should fail",
            "fact_content": "Because no authentication"
        }
        
        response = await client.post("/api/v1/myths-facts/", json=myth_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_myth_fact_validation_errors(self, client: AsyncClient, admin_headers: dict):
        """Test validation errors during creation"""
        # Missing required fields
        response = await client.post(
            "/api/v1/myths-facts/",
            json={},
            headers=admin_headers
        )
        assert response.status_code == 422
        
        # Empty title
        response = await client.post(
            "/api/v1/myths-facts/",
            json={
                "title": "",
                "myth_content": "Valid myth",
                "fact_content": "Valid fact"
            },
            headers=admin_headers
        )
        assert response.status_code == 422
        
        # Title too long
        response = await client.post(
            "/api/v1/myths-facts/",
            json={
                "title": "x" * 501,  # Exceeds 500 character limit
                "myth_content": "Valid myth",
                "fact_content": "Valid fact"
            },
            headers=admin_headers
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_myth_fact_invalid_category(self, client: AsyncClient, admin_headers: dict):
        """Test creation with invalid category ID"""
        myth_data = {
            "title": "Invalid Category Myth",
            "myth_content": "This myth has invalid category",
            "fact_content": "Should fail validation",
            "category_id": str(uuid4())  # Non-existent category
        }
        
        response = await client.post(
            "/api/v1/myths-facts/",
            json=myth_data,
            headers=admin_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "does not exist" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_myth_fact_by_id(self, client: AsyncClient, test_myth_fact: MythFact):
        """Test getting specific myth fact by ID"""
        response = await client.get(f"/api/v1/myths-facts/{test_myth_fact.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(test_myth_fact.id)
        assert data["title"] == test_myth_fact.title
        assert data["myth_statement"] == test_myth_fact.myth_content
        assert data["fact_explanation"] == test_myth_fact.fact_content
        assert data["image_url"] == test_myth_fact.image_url
        assert data["is_featured"] == test_myth_fact.is_featured

    @pytest.mark.asyncio
    async def test_get_myth_fact_not_found(self, client: AsyncClient):
        """Test getting non-existent myth fact"""
        non_existent_id = uuid4()
        response = await client.get(f"/api/v1/myths-facts/{non_existent_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_update_myth_fact_success(self, client: AsyncClient, admin_headers: dict, test_myth_fact: MythFact):
        """Test successful update of myth vs fact"""
        update_data = {
            "title": "Updated Myth Title",
            "myth_content": "Updated myth content",
            "is_featured": True
        }
        
        response = await client.put(
            f"/api/v1/myths-facts/{test_myth_fact.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Myth vs fact entry updated successfully"

    @pytest.mark.asyncio
    async def test_update_myth_fact_unauthorized(self, client: AsyncClient, auth_headers: dict, test_myth_fact: MythFact):
        """Test update fails for non-admin users"""
        update_data = {"title": "Should not update"}
        
        response = await client.put(
            f"/api/v1/myths-facts/{test_myth_fact.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_myth_fact_not_found(self, client: AsyncClient, admin_headers: dict):
        """Test update of non-existent myth fact"""
        non_existent_id = uuid4()
        update_data = {"title": "Should not work"}
        
        response = await client.put(
            f"/api/v1/myths-facts/{non_existent_id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_myth_fact_success(self, client: AsyncClient, admin_headers: dict, test_myth_fact: MythFact):
        """Test successful deletion of myth vs fact"""
        response = await client.delete(
            f"/api/v1/myths-facts/{test_myth_fact.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Myth vs fact entry deleted successfully"
        
        # Verify it's actually deleted
        get_response = await client.get(f"/api/v1/myths-facts/{test_myth_fact.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_myth_fact_unauthorized(self, client: AsyncClient, auth_headers: dict, test_myth_fact: MythFact):
        """Test delete fails for non-admin users"""
        response = await client.delete(
            f"/api/v1/myths-facts/{test_myth_fact.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_myth_fact_not_found(self, client: AsyncClient, admin_headers: dict):
        """Test delete of non-existent myth fact"""
        non_existent_id = uuid4()
        
        response = await client.delete(
            f"/api/v1/myths-facts/{non_existent_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_myths_for_frontend(self, client: AsyncClient, test_myth_fact: MythFact, featured_myth_fact: MythFact):
        """Test frontend-specific endpoint"""
        response = await client.get("/api/v1/myths-facts/resources/myths")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_get_myths_for_frontend_featured_only(self, client: AsyncClient, test_myth_fact: MythFact, featured_myth_fact: MythFact):
        """Test frontend endpoint with featured filter"""
        response = await client.get("/api/v1/myths-facts/resources/myths?featured_only=true")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only return featured items
        for item in data["items"]:
            assert item["is_featured"] is True

    @pytest.mark.asyncio
    async def test_get_random_seven_myths(self, client: AsyncClient, test_db: AsyncSession, test_category: Category):
        """Test random seven myths endpoint for game"""
        # Create more than 7 myth facts
        for i in range(10):
            myth_fact = MythFact(
                title=f"Random Myth {i}",
                myth_content=f"Random myth content {i}",
                fact_content=f"Random fact content {i}",
                category_id=test_category.id
            )
            test_db.add(myth_fact)
        await test_db.commit()
        
        response = await client.get("/api/v1/myths-facts/resources/random7")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of items (up to 7)
        assert isinstance(data, list)
        assert len(data) <= 7
        
        # Check structure of game response
        if data:
            item = data[0]
            assert "id" in item
            assert "title" in item
            assert "myth_statement" in item
            assert "fact_explanation" in item
            assert "image_url" in item
            assert "is_featured" in item
            # Should not include category in game response
            assert "category" not in item

    @pytest.mark.asyncio
    async def test_database_error_handling(self, client: AsyncClient):
        """Test graceful handling of database errors"""
        # Test frontend endpoint with database error simulation
        with patch('app.api.endpoints.myths_facts.select') as mock_select:
            mock_select.side_effect = Exception("Database connection failed")
            
            response = await client.get("/api/v1/myths-facts/resources/myths")
            
            # Should return empty result instead of error for frontend resilience
            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["pagination"]["total"] == 0

    @pytest.mark.asyncio
    async def test_random_endpoint_database_error(self, client: AsyncClient):
        """Test random endpoint with database error"""
        with patch('app.api.endpoints.myths_facts.select') as mock_select:
            mock_select.side_effect = Exception("Database error")
            
            response = await client.get("/api/v1/myths-facts/resources/random7")
            
            # Should return empty list for graceful frontend handling
            assert response.status_code == 200
            data = response.json()
            assert data == []

    @pytest.mark.asyncio
    async def test_invalid_uuid_parameters(self, client: AsyncClient):
        """Test handling of invalid UUID parameters"""
        # Invalid UUID in path
        response = await client.get("/api/v1/myths-facts/invalid-uuid")
        assert response.status_code == 422
        
        # Invalid UUID in query parameter
        response = await client.get("/api/v1/myths-facts/?category_id=invalid-uuid")
        # Should still work, just ignore the invalid filter
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, client: AsyncClient):
        """Test pagination edge cases"""
        # Page 0 should be rejected
        response = await client.get("/api/v1/myths-facts/?page=0")
        assert response.status_code == 422
        
        # Negative page should be rejected
        response = await client.get("/api/v1/myths-facts/?page=-1")
        assert response.status_code == 422
        
        # Limit too high should be rejected
        response = await client.get("/api/v1/myths-facts/?limit=100")
        assert response.status_code == 422
        
        # Limit 0 should be rejected
        response = await client.get("/api/v1/myths-facts/?limit=0")
        assert response.status_code == 422


class TestMythsFactsSchemas:
    """Test Pydantic schemas for myths vs facts"""

    def test_myth_fact_create_schema_validation(self):
        """Test MythFactCreate schema validation"""
        # Valid data
        valid_data = {
            "title": "Test Title",
            "myth_content": "Test myth",
            "fact_content": "Test fact"
        }
        schema = MythFactCreate(**valid_data)
        assert schema.title == "Test Title"
        assert schema.myth_content == "Test myth"
        assert schema.fact_content == "Test fact"
        assert schema.is_featured is False
        
        # Test with all fields
        full_data = {
            "title": "Full Test",
            "myth_content": "Full myth",
            "fact_content": "Full fact",
            "image_url": "https://example.com/image.jpg",
            "category_id": uuid4(),
            "is_featured": True
        }
        schema = MythFactCreate(**full_data)
        assert schema.is_featured is True
        assert schema.image_url == "https://example.com/image.jpg"

    def test_myth_fact_create_validation_errors(self):
        """Test validation errors in MythFactCreate"""
        from pydantic import ValidationError
        
        # Empty title
        with pytest.raises(ValidationError):
            MythFactCreate(title="", myth_content="myth", fact_content="fact")
        
        # Empty myth content
        with pytest.raises(ValidationError):
            MythFactCreate(title="title", myth_content="", fact_content="fact")
        
        # Empty fact content
        with pytest.raises(ValidationError):
            MythFactCreate(title="title", myth_content="myth", fact_content="")
        
        # Invalid image URL
        with pytest.raises(ValidationError):
            MythFactCreate(
                title="title",
                myth_content="myth", 
                fact_content="fact",
                image_url="invalid-url"
            )

    def test_myth_fact_update_schema(self):
        """Test MythFactUpdate schema"""
        # Partial update
        update_data = {"title": "Updated Title"}
        schema = MythFactUpdate(**update_data)
        assert schema.title == "Updated Title"
        assert schema.myth_content is None
        
        # Empty update should be valid
        schema = MythFactUpdate()
        assert schema.title is None
        assert schema.myth_content is None

    def test_image_url_validation(self):
        """Test image URL validation"""
        # Valid URLs
        valid_urls = [
            "https://example.com/image.jpg",
            "http://example.com/image.png",
            "/static/images/test.jpg",
            None,
            ""
        ]
        
        for url in valid_urls:
            schema = MythFactCreate(
                title="Test",
                myth_content="myth",
                fact_content="fact",
                image_url=url
            )
            if url and url.strip():
                assert schema.image_url == url
            else:
                assert schema.image_url is None

    def test_string_trimming(self):
        """Test that strings are properly trimmed"""
        schema = MythFactCreate(
            title="  Trimmed Title  ",
            myth_content="  Trimmed Myth  ",
            fact_content="  Trimmed Fact  "
        )
        
        assert schema.title == "Trimmed Title"
        assert schema.myth_content == "Trimmed Myth"
        assert schema.fact_content == "Trimmed Fact"