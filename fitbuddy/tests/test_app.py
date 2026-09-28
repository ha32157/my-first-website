def valid_payload():
    return {
        "user_id": "test-001",
        "name": "Test User",
        "age": 30,
        "weight_kg": 70,
        "goal": "general wellness",
        "intensity": "medium",
    }


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Generate 7-day plan" in response.text


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["ai_mode"] == "demo"


def test_generate_workout_api(client):
    response = client.post("/api/workouts", json=valid_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == "test-001"
    assert "Day 1" in body["workout_plan"]
    assert body["nutrition_tip"]


def test_feedback_updates_plan(client):
    client.post("/api/workouts", json=valid_payload())
    response = client.post("/api/workouts/test-001/feedback", json={"feedback": "Add more cardio and another rest day."})
    assert response.status_code == 200
    body = response.json()
    assert body["updated"] is True
    assert "UPDATED FROM USER FEEDBACK" in body["workout_plan"]


def test_validation_rejects_invalid_age(client):
    payload = valid_payload()
    payload["age"] = 8
    response = client.post("/api/workouts", json=payload)
    assert response.status_code == 422


def test_user_lookup(client):
    client.post("/api/workouts", json=valid_payload())
    response = client.get("/api/users/test-001")
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"


def test_admin_requires_key(client):
    assert client.get("/api/users").status_code == 401
    assert client.get("/api/users", headers={"X-Admin-Key": "test-admin"}).status_code == 200


def test_web_feedback(client):
    client.post("/generate-workout", data=valid_payload())
    response = client.post("/submit-feedback", data={"user_id": "test-001", "feedback": "Add yoga and more recovery."})
    assert response.status_code == 200
    assert "updated successfully" in response.text
