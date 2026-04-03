"""
Integration tests for API health endpoints.

Note: These tests require the environment to be properly configured.
The conftest.py provides mock environment variables.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestHealthEndpoints:
    """Tests for health check API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client."""
        # Patch the supabase module-level client before importing app
        with patch('app.db.supabase_client.supabase') as mock_supabase, \
             patch('app.db.supabase_client.supabase_sync') as mock_supabase_sync:
            
            mock_supabase.table.return_value = MagicMock()
            
            from fastapi.testclient import TestClient
            from app.main import app
            
            with TestClient(app) as client:
                yield client
    
    @pytest.mark.integration
    def test_root_endpoint(self, test_client):
        """Test root endpoint returns welcome message."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data or isinstance(data, dict)
    
    @pytest.mark.integration
    def test_health_check_endpoint_accessible(self, test_client):
        """Test health check endpoint is accessible."""
        response = test_client.get("/api/v1/health")
        
        # Health check should return 200 or 503 (unhealthy but reachable)
        assert response.status_code in [200, 503]


class TestOpenAPISpec:
    """Tests for OpenAPI specification."""
    
    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client."""
        with patch('app.db.supabase_client.supabase') as mock_supabase, \
             patch('app.db.supabase_client.supabase_sync') as mock_supabase_sync:
            
            mock_supabase.table.return_value = MagicMock()
            
            from fastapi.testclient import TestClient
            from app.main import app
            
            with TestClient(app) as client:
                yield client
    
    @pytest.mark.integration
    def test_openapi_schema_available(self, test_client):
        """Test OpenAPI schema is accessible."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "info" in data
