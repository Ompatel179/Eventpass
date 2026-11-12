def test_home_serves_attendee_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_organizer_page_is_served(client):
    response = client.get("/organizer")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_static_files_are_served(client):
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]