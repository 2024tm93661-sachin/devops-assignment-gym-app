"""
ACEest Fitness & Gym - Flask Web Application
Core API for the CI/CD pipeline assignment.
"""
from flask import Flask, jsonify, request

app = Flask(__name__)

# ── In-memory data store (no DB needed for Flask API layer) ──────────────────
PROGRAMS = {
    "Fat Loss (FL)":   {"factor": 22, "color": "#e74c3c"},
    "Muscle Gain (MG)": {"factor": 35, "color": "#2ecc71"},
    "Beginner (BG)":   {"factor": 26, "color": "#3498db"},
}

clients = {}   # { name: {age, weight, program, calories, adherence} }
progress = []  # [ {client_name, week, adherence} ]


# ── Health check ─────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "app": "ACEest Fitness & Gym API", "version": "1.0.0"})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


# ── Programs ─────────────────────────────────────────────────────────────────
@app.route("/programs", methods=["GET"])
def get_programs():
    """Return all available fitness programs."""
    return jsonify({"programs": list(PROGRAMS.keys())}), 200


# ── Calorie Calculator ────────────────────────────────────────────────────────
@app.route("/calculate_calories", methods=["POST"])
def calculate_calories():
    """
    Calculate daily calorie target.
    Body: { "weight_kg": float, "program": str }
    """
    data = request.get_json(force=True, silent=True) or {}
    weight = data.get("weight_kg")
    program = data.get("program")

    if weight is None or program is None:
        return jsonify({"error": "weight_kg and program are required"}), 400
    if not isinstance(weight, (int, float)) or weight <= 0:
        return jsonify({"error": "weight_kg must be a positive number"}), 400
    if program not in PROGRAMS:
        return jsonify({"error": f"Unknown program. Choose from: {list(PROGRAMS.keys())}"}), 400

    calories = int(weight * PROGRAMS[program]["factor"])
    return jsonify({"weight_kg": weight, "program": program, "calories_per_day": calories}), 200


# ── Client Management ─────────────────────────────────────────────────────────
@app.route("/clients", methods=["GET"])
def list_clients():
    """List all registered clients."""
    return jsonify({"clients": list(clients.values())}), 200


@app.route("/clients", methods=["POST"])
def add_client():
    """
    Register / update a client.
    Body: { "name": str, "age": int, "weight_kg": float, "program": str, "adherence": int }
    """
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name", "").strip()
    age = data.get("age")
    weight = data.get("weight_kg")
    program = data.get("program")
    adherence = data.get("adherence", 0)

    if not name:
        return jsonify({"error": "name is required"}), 400
    if program not in PROGRAMS:
        return jsonify({"error": f"Invalid program. Choose: {list(PROGRAMS.keys())}"}), 400
    if not isinstance(weight, (int, float)) or weight <= 0:
        return jsonify({"error": "weight_kg must be a positive number"}), 400

    calories = int(weight * PROGRAMS[program]["factor"])
    clients[name] = {
        "name":             name,
        "age":              age,
        "weight_kg":        weight,
        "program":          program,
        "calories_per_day": calories,
        "adherence":        adherence,
    }
    return jsonify({"message": "Client saved", "client": clients[name]}), 201


@app.route("/clients/<string:name>", methods=["GET"])
def get_client(name):
    """Fetch a single client by name."""
    client = clients.get(name)
    if not client:
        return jsonify({"error": "Client not found"}), 404
    return jsonify({"client": client}), 200


# ── Progress Logging ──────────────────────────────────────────────────────────
@app.route("/progress", methods=["POST"])
def log_progress():
    """
    Log weekly adherence progress.
    Body: { "client_name": str, "week": str, "adherence": int }
    """
    data = request.get_json(force=True, silent=True) or {}
    client_name = data.get("client_name", "").strip()
    week = data.get("week", "").strip()
    adherence = data.get("adherence")

    if not client_name or not week or adherence is None:
        return jsonify({"error": "client_name, week, and adherence are required"}), 400
    if client_name not in clients:
        return jsonify({"error": "Client not found. Register the client first."}), 404
    if not (0 <= adherence <= 100):
        return jsonify({"error": "adherence must be between 0 and 100"}), 400

    entry = {"client_name": client_name, "week": week, "adherence": adherence}
    progress.append(entry)
    return jsonify({"message": "Progress logged", "entry": entry}), 201


@app.route("/progress/<string:name>", methods=["GET"])
def get_progress(name):
    """Fetch progress history for a client."""
    if name not in clients:
        return jsonify({"error": "Client not found"}), 404
    history = [p for p in progress if p["client_name"] == name]
    return jsonify({"client_name": name, "progress": history}), 200


# ── BMI Helper ────────────────────────────────────────────────────────────────
@app.route("/bmi", methods=["POST"])
def calculate_bmi():
    """
    Body: { "weight_kg": float, "height_m": float }
    """
    data = request.get_json(force=True, silent=True) or {}
    weight = data.get("weight_kg")
    height = data.get("height_m")

    if weight is None or height is None:
        return jsonify({"error": "weight_kg and height_m are required"}), 400
    if height <= 0 or weight <= 0:
        return jsonify({"error": "Values must be positive"}), 400

    bmi = round(weight / (height ** 2), 2)
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25.0:
        category = "Normal"
    elif bmi < 30.0:
        category = "Overweight"
    else:
        category = "Obese"

    return jsonify({"bmi": bmi, "category": category}), 200


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)