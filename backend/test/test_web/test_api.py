

def test_healthz_endpoint(client):
    """Simple test that doesn't require database"""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == "OK"
    
def test_register(client):
    response = client.post(
        "/api/v1/management/register", 
        json={
            "username": "luntaixia", 
            "password": "password123"
        }
    )
    assert response.status_code == 200
    
    
def test_entity_endpoint(authorized_client):
    response = authorized_client.get("/api/v1/entity/contact/list")
    assert response.status_code == 200
    assert response.json() == []