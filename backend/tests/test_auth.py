def test_register_user_success(client):
    payload = {
        "username": "newtrader",
        "email": "newtrader@example.com",
        "password": "Password123!",
    }
    response = client.post("/api/v1/users/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newtrader"
    assert data["email"] == "newtrader@example.com"
    assert data["is_active"] is True
    assert "id" in data


def test_register_user_duplicate_email(client, test_user):
    payload = {
        "username": "unique_username",
        "email": test_user.email,  # duplicate
        "password": "Password123!",
    }
    response = client.post("/api/v1/users/", json=payload)
    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]


def test_register_user_duplicate_username(client, test_user):
    payload = {
        "username": test_user.username,  # duplicate
        "email": "different@example.com",
        "password": "Password123!",
    }
    response = client.post("/api/v1/users/", json=payload)
    assert response.status_code == 409
    assert "Username already registered" in response.json()["detail"]


def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/users/login",
        data={
            "username": test_user.email,
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client, test_user):
    response = client.post(
        "/api/v1/users/login",
        data={
            "username": test_user.email,
            "password": "WrongPassword!",
        },
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_get_me_success(client, auth_headers, test_user):
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email


def test_get_me_unauthorized(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
