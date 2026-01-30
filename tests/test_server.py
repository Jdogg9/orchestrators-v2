"""Basic smoke tests for ORCHESTRATORS_V2 server."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Verify core modules can be imported."""
    from src import server
    assert server is not None

def test_health_endpoint_exists():
    """Verify health endpoint is defined."""
    from src.server import app
    
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data
        assert data['status'] == 'ok'


def test_ready_endpoint_exists():
    """Verify readiness endpoint is defined."""
    from src.server import app

    with app.test_client() as client:
        response = client.get('/ready')
        assert response.status_code in (200, 503)

def test_echo_endpoint():
    """Verify echo endpoint works."""
    from src.server import app
    
    with app.test_client() as client:
        response = client.post('/echo', 
                              json={'message': 'test'},
                              headers={'Content-Type': 'application/json'})
        assert response.status_code == 200
        data = response.get_json()
        assert 'echo' in data
        assert data['echo'] == 'test'
