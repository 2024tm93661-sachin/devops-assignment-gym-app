"""
ACEest Fitness & Gym – Pytest Test Suite
Tests all Flask API endpoints for correctness and edge cases.
"""

import pytest
from app import app, clients, progress, PROGRAMS


@pytest.fixture(autouse=True)
def reset_state():
    """Clear in-memory stores before every test for isolation."""
    clients.clear()
    progress.clear()
    yield
    clients.clear()
    progress.clear()


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Health & Index ────────────────────────────────────────────────────────────

class TestHealthEndpoints:
    def test_index_returns_ok(self, client):
        res = client.get("/")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert "ACEest" in data["app"]

    def test_health_returns_healthy(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.get_json()["status"] == "healthy"


# ── Programs ─────────────────────────────────────────────────────────────────

class TestPrograms:
    def test_get_programs_returns_list(self, client):
        res = client.get("/programs")
        assert res.status_code == 200
        data = res.get_json()
        assert "programs" in data
        assert len(data["programs"]) == 3

    def test_all_expected_programs_present(self, client):
        res = client.get("/programs")
        programs = res.get_json()["programs"]
        assert "Fat Loss (FL)" in programs
        assert "Muscle Gain (MG)" in programs
        assert "Beginner (BG)" in programs


# ── Calorie Calculator ────────────────────────────────────────────────────────

class TestCalorieCalculator:
    def test_fat_loss_calories(self, client):
        res = client.post("/calculate_calories",
                          json={"weight_kg": 70, "program": "Fat Loss (FL)"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["calories_per_day"] == 70 * 22          # factor = 22

    def test_muscle_gain_calories(self, client):
        res = client.post("/calculate_calories",
                          json={"weight_kg": 80, "program": "Muscle Gain (MG)"})
        assert res.status_code == 200
        assert res.get_json()["calories_per_day"] == 80 * 35

    def test_beginner_calories(self, client):
        res = client.post("/calculate_calories",
                          json={"weight_kg": 60, "program": "Beginner (BG)"})
        assert res.status_code == 200
        assert res.get_json()["calories_per_day"] == 60 * 26

    def test_missing_weight_returns_400(self, client):
        res = client.post("/calculate_calories",
                          json={"program": "Beginner (BG)"})
        assert res.status_code == 400

    def test_missing_program_returns_400(self, client):
        res = client.post("/calculate_calories",
                          json={"weight_kg": 70})
        assert res.status_code == 400

    def test_invalid_program_returns_400(self, client):
        res = client.post("/calculate_calories",
                          json={"weight_kg": 70, "program": "Ultra Gains"})
        assert res.status_code == 400

    def test_negative_weight_returns_400(self, client):
        res = client.post("/calculate_calories",
                          json={"weight_kg": -10, "program": "Beginner (BG)"})
        assert res.status_code == 400

    def test_zero_weight_returns_400(self, client):
        res = client.post("/calculate_calories",
                          json={"weight_kg": 0, "program": "Beginner (BG)"})
        assert res.status_code == 400


# ── Client Management ─────────────────────────────────────────────────────────

class TestClientManagement:
    VALID_CLIENT = {
        "name": "Arjun",
        "age": 28,
        "weight_kg": 75,
        "program": "Muscle Gain (MG)",
        "adherence": 80
    }

    def test_add_client_success(self, client):
        res = client.post("/clients", json=self.VALID_CLIENT)
        assert res.status_code == 201
        data = res.get_json()
        assert data["client"]["name"] == "Arjun"
        assert data["client"]["calories_per_day"] == 75 * 35

    def test_add_client_calculates_calories(self, client):
        res = client.post("/clients", json=self.VALID_CLIENT)
        assert res.get_json()["client"]["calories_per_day"] == 75 * 35

    def test_list_clients_empty(self, client):
        res = client.get("/clients")
        assert res.status_code == 200
        assert res.get_json()["clients"] == []

    def test_list_clients_after_add(self, client):
        client.post("/clients", json=self.VALID_CLIENT)
        res = client.get("/clients")
        assert len(res.get_json()["clients"]) == 1

    def test_get_existing_client(self, client):
        client.post("/clients", json=self.VALID_CLIENT)
        res = client.get("/clients/Arjun")
        assert res.status_code == 200
        assert res.get_json()["client"]["name"] == "Arjun"

    def test_get_nonexistent_client_404(self, client):
        res = client.get("/clients/Ghost")
        assert res.status_code == 404

    def test_add_client_missing_name(self, client):
        bad = dict(self.VALID_CLIENT)
        bad.pop("name")
        res = client.post("/clients", json=bad)
        assert res.status_code == 400

    def test_add_client_invalid_program(self, client):
        bad = dict(self.VALID_CLIENT)
        bad["program"] = "Zumba Elite"
        res = client.post("/clients", json=bad)
        assert res.status_code == 400

    def test_add_client_invalid_weight(self, client):
        bad = dict(self.VALID_CLIENT)
        bad["weight_kg"] = 0
        res = client.post("/clients", json=bad)
        assert res.status_code == 400

    def test_update_existing_client(self, client):
        client.post("/clients", json=self.VALID_CLIENT)
        updated = dict(self.VALID_CLIENT)
        updated["weight_kg"] = 80
        res = client.post("/clients", json=updated)
        assert res.status_code == 201
        assert res.get_json()["client"]["weight_kg"] == 80


# ── Progress Logging ──────────────────────────────────────────────────────────

class TestProgress:
    def _register(self, client):
        client.post("/clients", json={
            "name": "Priya",
            "age": 25,
            "weight_kg": 58,
            "program": "Fat Loss (FL)",
            "adherence": 90
        })

    def test_log_progress_success(self, client):
        self._register(client)
        res = client.post("/progress", json={
            "client_name": "Priya",
            "week": "Week 01 - 2025",
            "adherence": 85
        })
        assert res.status_code == 201

    def test_get_progress_history(self, client):
        self._register(client)
        client.post("/progress", json={"client_name": "Priya", "week": "Week 01", "adherence": 80})
        client.post("/progress", json={"client_name": "Priya", "week": "Week 02", "adherence": 90})
        res = client.get("/progress/Priya")
        assert res.status_code == 200
        assert len(res.get_json()["progress"]) == 2

    def test_log_progress_unknown_client(self, client):
        res = client.post("/progress", json={
            "client_name": "NoOne",
            "week": "Week 01",
            "adherence": 70
        })
        assert res.status_code == 404

    def test_adherence_out_of_range(self, client):
        self._register(client)
        res = client.post("/progress", json={
            "client_name": "Priya",
            "week": "Week 01",
            "adherence": 150
        })
        assert res.status_code == 400

    def test_missing_fields_returns_400(self, client):
        self._register(client)
        res = client.post("/progress", json={"client_name": "Priya"})
        assert res.status_code == 400

    def test_progress_for_unknown_client_get(self, client):
        res = client.get("/progress/Unknown")
        assert res.status_code == 404


# ── BMI ───────────────────────────────────────────────────────────────────────

class TestBMI:
    def test_normal_bmi(self, client):
        res = client.post("/bmi", json={"weight_kg": 70, "height_m": 1.75})
        assert res.status_code == 200
        data = res.get_json()
        assert data["category"] == "Normal"
        assert data["bmi"] == round(70 / (1.75 ** 2), 2)

    def test_underweight(self, client):
        res = client.post("/bmi", json={"weight_kg": 45, "height_m": 1.75})
        assert res.status_code == 200
        assert res.get_json()["category"] == "Underweight"

    def test_overweight(self, client):
        res = client.post("/bmi", json={"weight_kg": 90, "height_m": 1.75})
        assert res.status_code == 200
        assert res.get_json()["category"] == "Overweight"

    def test_obese(self, client):
        res = client.post("/bmi", json={"weight_kg": 120, "height_m": 1.70})
        assert res.status_code == 200
        assert res.get_json()["category"] == "Obese"

    def test_missing_height_returns_400(self, client):
        res = client.post("/bmi", json={"weight_kg": 70})
        assert res.status_code == 400

    def test_zero_height_returns_400(self, client):
        res = client.post("/bmi", json={"weight_kg": 70, "height_m": 0})
        assert res.status_code == 400


# ── Calorie Logic Unit Tests (pure functions, no HTTP) ────────────────────────

class TestCalorieLogicUnit:
    """Test the calorie formula directly without HTTP overhead."""

    def test_factor_fat_loss(self):
        assert PROGRAMS["Fat Loss (FL)"]["factor"] == 22

    def test_factor_muscle_gain(self):
        assert PROGRAMS["Muscle Gain (MG)"]["factor"] == 35

    def test_factor_beginner(self):
        assert PROGRAMS["Beginner (BG)"]["factor"] == 26

    def test_calorie_formula(self):
        weight, factor = 70, 22
        assert int(weight * factor) == 1540

    def test_three_programs_defined(self):
        assert len(PROGRAMS) == 3
