"""
Integration tests for complete myths vs facts flow
Tests the complete flow from API to frontend integration
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
import json

from app.models.myth_fact import MythFact
from app.models.category import Category
from app.models.user import User


class TestMythsFactsIntegration:
    """Integration tests for complete myths vs facts functionality"""

    @pytest.fixture
    async def sample_myth_facts(self, test_db: AsyncSession, test_category: Category):
        """Create sample myth facts for integration testing"""
        myth_facts = []
        
        # Create a mix of myths and facts
        sample_data = [
            {
                "title": "Integration Test Myth 1",
                "myth_content": "All snakes in India are venomous and dangerous",
                "fact_content": "Most Indian snakes are non-venomous and help control pest populations",
                "type": "myth",
                "is_featured": True
            },
            {
                "title": "Integration Test Fact 1", 
                "myth_content": "Elephants have excellent long-term memory",
                "fact_content": "Elephants can remember other elephants and locations for decades",
                "type": "fact",
                "is_featured": False
            },
            {
                "title": "Integration Test Myth 2",
                "myth_content": "Tigers hunt primarily during daylight hours",
                "fact_content": "Tigers are nocturnal hunters and prefer dawn and dusk",
                "type": "myth", 
                "is_featured": True
            },
            {
                "title": "Integration Test Fact 2",
                "myth_content": "Leopards can carry prey up into trees",
                "fact_content": "Leopards are excellent climbers and store prey in trees for protection",
                "type": "fact",
                "is_featured": False
            }
        ]
        
        for data in sample_data:
            myth_fact = MythFact(
                title=data["title"],
                myth_content=data["myth_content"],
                fact_content=data["fact_content"],
                category_id=test_category.id,
                is_featured=data["is_featured"],
                image_url=f"/test/images/{data['type']}.jpg"
            )
            test_db.add(myth_fact)
            myth_facts.append(myth_fact)
        
        await test_db.commit()
        for myth_fact in myth_facts:
            await test_db.refresh(myth_fact)
        
        return myth_facts

    @pytest.mark.asyncio
    async def test_complete_crud_flow(self, client: AsyncClient, admin_headers: dict, test_category: Category):
        """Test complete CRUD flow for myths vs facts"""
        
        # 1. Create a new myth vs fact
        create_data = {
            "title": "CRUD Test Myth vs Fact",
            "myth_content": "This is a test myth for CRUD operations",
            "fact_content": "This is the corresponding fact explanation",
            "category_id": str(test_category.id),
            "is_featured": True,
            "image_url": "/test/crud-image.jpg"
        }
        
        create_response = await client.post(
            "/api/v1/myths-facts/",
            json=create_data,
            headers=admin_headers
        )
        
        assert create_response.status_code == 201
        create_result = create_response.json()
        myth_fact_id = create_result["data"]["id"]
        
        # 2. Read the created myth vs fact
        read_response = await client.get(f"/api/v1/myths-facts/{myth_fact_id}")
        
        assert read_response.status_code == 200
        read_result = read_response.json()
        
        assert read_result["title"] == create_data["title"]
        assert read_result["myth_statement"] == create_data["myth_content"]
        assert read_result["fact_explanation"] == create_data["fact_content"]
        assert read_result["is_featured"] == create_data["is_featured"]
        
        # 3. Update the myth vs fact
        update_data = {
            "title": "Updated CRUD Test Myth vs Fact",
            "myth_content": "Updated myth content",
            "is_featured": False
        }
        
        update_response = await client.put(
            f"/api/v1/myths-facts/{myth_fact_id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert update_response.status_code == 200
        
        # Verify update
        updated_read_response = await client.get(f"/api/v1/myths-facts/{myth_fact_id}")
        updated_result = updated_read_response.json()
        
        assert updated_result["title"] == update_data["title"]
        assert updated_result["myth_statement"] == update_data["myth_content"]
        assert updated_result["is_featured"] == update_data["is_featured"]
        
        # 4. Delete the myth vs fact
        delete_response = await client.delete(
            f"/api/v1/myths-facts/{myth_fact_id}",
            headers=admin_headers
        )
        
        assert delete_response.status_code == 200
        
        # Verify deletion
        deleted_read_response = await client.get(f"/api/v1/myths-facts/{myth_fact_id}")
        assert deleted_read_response.status_code == 404

    @pytest.mark.asyncio
    async def test_frontend_api_integration(self, client: AsyncClient, sample_myth_facts):
        """Test API endpoints used by frontend game interface"""
        
        # Test regular myths vs facts endpoint
        response = await client.get("/api/v1/myths-facts/resources/myths")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) >= 4  # Our sample data
        
        # Verify data structure for frontend
        item = data["items"][0]
        required_fields = ["id", "title", "myth_statement", "fact_explanation", "category", "image_url", "created_at", "is_featured"]
        for field in required_fields:
            assert field in item
        
        # Test random myths endpoint for game
        random_response = await client.get("/api/v1/myths-facts/resources/random7")
        
        assert random_response.status_code == 200
        random_data = random_response.json()
        
        assert isinstance(random_data, list)
        assert len(random_data) <= 7
        
        # Verify game-specific data structure
        if random_data:
            game_item = random_data[0]
            game_fields = ["id", "title", "myth_statement", "fact_explanation", "image_url", "is_featured"]
            for field in game_fields:
                assert field in game_item

    @pytest.mark.asyncio
    async def test_pagination_and_filtering(self, client: AsyncClient, sample_myth_facts, test_category: Category):
        """Test pagination and filtering functionality"""
        
        # Test pagination
        page1_response = await client.get("/api/v1/myths-facts/?page=1&limit=2")
        assert page1_response.status_code == 200
        page1_data = page1_response.json()
        
        assert len(page1_data["items"]) <= 2
        assert page1_data["pagination"]["page"] == 1
        assert page1_data["pagination"]["limit"] == 2
        
        # Test featured filter
        featured_response = await client.get("/api/v1/myths-facts/?featured_only=true")
        assert featured_response.status_code == 200
        featured_data = featured_response.json()
        
        # All returned items should be featured
        for item in featured_data["items"]:
            assert item["is_featured"] is True
        
        # Test category filter
        category_response = await client.get(f"/api/v1/myths-facts/?category_id={test_category.id}")
        assert category_response.status_code == 200
        category_data = category_response.json()
        
        # All returned items should be from the test category
        for item in category_data["items"]:
            assert item["category"] == test_category.name

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, client: AsyncClient, admin_headers: dict):
        """Test error handling across the complete flow"""
        
        # Test validation errors
        invalid_data = {
            "title": "",  # Empty title should fail
            "myth_content": "",  # Empty content should fail
            "fact_content": ""   # Empty content should fail
        }
        
        validation_response = await client.post(
            "/api/v1/myths-facts/",
            json=invalid_data,
            headers=admin_headers
        )
        
        assert validation_response.status_code == 422
        
        # Test not found errors
        non_existent_id = uuid4()
        not_found_response = await client.get(f"/api/v1/myths-facts/{non_existent_id}")
        assert not_found_response.status_code == 404
        
        # Test unauthorized access
        unauthorized_response = await client.post("/api/v1/myths-facts/", json={"title": "test"})
        assert unauthorized_response.status_code == 401

    @pytest.mark.asyncio
    async def test_data_consistency(self, client: AsyncClient, admin_headers: dict, test_category: Category):
        """Test data consistency across different endpoints"""
        
        # Create myth vs fact via API
        create_data = {
            "title": "Consistency Test",
            "myth_content": "Consistency test myth",
            "fact_content": "Consistency test fact",
            "category_id": str(test_category.id),
            "is_featured": True
        }
        
        create_response = await client.post(
            "/api/v1/myths-facts/",
            json=create_data,
            headers=admin_headers
        )
        
        myth_fact_id = create_response.json()["data"]["id"]
        
        # Verify data appears consistently across all endpoints
        
        # 1. Individual fetch
        individual_response = await client.get(f"/api/v1/myths-facts/{myth_fact_id}")
        individual_data = individual_response.json()
        
        # 2. List fetch
        list_response = await client.get("/api/v1/myths-facts/")
        list_data = list_response.json()
        list_item = next((item for item in list_data["items"] if item["id"] == myth_fact_id), None)
        
        # 3. Frontend fetch
        frontend_response = await client.get("/api/v1/myths-facts/resources/myths")
        frontend_data = frontend_response.json()
        frontend_item = next((item for item in frontend_data["items"] if item["id"] == myth_fact_id), None)
        
        # Verify consistency
        assert individual_data["title"] == create_data["title"]
        assert list_item["title"] == create_data["title"]
        assert frontend_item["title"] == create_data["title"]
        
        assert individual_data["is_featured"] == create_data["is_featured"]
        assert list_item["is_featured"] == create_data["is_featured"]
        assert frontend_item["is_featured"] == create_data["is_featured"]

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, client: AsyncClient, admin_headers: dict, test_category: Category):
        """Test handling of concurrent operations"""
        import asyncio
        
        async def create_myth_fact(index):
            data = {
                "title": f"Concurrent Test {index}",
                "myth_content": f"Concurrent myth {index}",
                "fact_content": f"Concurrent fact {index}",
                "category_id": str(test_category.id)
            }
            
            response = await client.post(
                "/api/v1/myths-facts/",
                json=data,
                headers=admin_headers
            )
            return response
        
        # Create multiple myth facts concurrently
        tasks = [create_myth_fact(i) for i in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations succeeded
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) == 5
        
        for response in successful_responses:
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_performance_under_load(self, client: AsyncClient, sample_myth_facts):
        """Test API performance under load"""
        import time
        import asyncio
        
        async def fetch_myths_facts():
            start_time = time.time()
            response = await client.get("/api/v1/myths-facts/resources/myths")
            end_time = time.time()
            return response, end_time - start_time
        
        # Make multiple concurrent requests
        tasks = [fetch_myths_facts() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        for response, duration in results:
            assert response.status_code == 200
            assert duration < 2.0  # Should respond within 2 seconds
        
        # Verify average response time is reasonable
        avg_duration = sum(duration for _, duration in results) / len(results)
        assert avg_duration < 1.0  # Average should be under 1 second

    @pytest.mark.asyncio
    async def test_data_transformation_consistency(self, client: AsyncClient, sample_myth_facts):
        """Test that data transformation is consistent across endpoints"""
        
        # Get data from different endpoints
        list_response = await client.get("/api/v1/myths-facts/")
        frontend_response = await client.get("/api/v1/myths-facts/resources/myths")
        random_response = await client.get("/api/v1/myths-facts/resources/random7")
        
        assert list_response.status_code == 200
        assert frontend_response.status_code == 200
        assert random_response.status_code == 200
        
        list_data = list_response.json()
        frontend_data = frontend_response.json()
        random_data = random_response.json()
        
        # Find common items and verify transformation consistency
        if list_data["items"] and frontend_data["items"]:
            list_item = list_data["items"][0]
            frontend_item = next(
                (item for item in frontend_data["items"] if item["id"] == list_item["id"]), 
                None
            )
            
            if frontend_item:
                # Verify field mapping consistency
                assert list_item["myth_statement"] == frontend_item["myth_statement"]
                assert list_item["fact_explanation"] == frontend_item["fact_explanation"]
                assert list_item["is_featured"] == frontend_item["is_featured"]
        
        # Verify random endpoint returns proper game format
        if random_data:
            random_item = random_data[0]
            required_game_fields = ["id", "title", "myth_statement", "fact_explanation", "image_url", "is_featured"]
            for field in required_game_fields:
                assert field in random_item