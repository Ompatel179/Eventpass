def test_scanner_page_is_served(client):
    response = client.get("/scanner")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "EventPass Scanner" in response.text