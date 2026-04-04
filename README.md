<<<<<<< HEAD
# bits-pilani
dev-ops assignment 1
=======
# ACEest Fitness & Gym — CI/CD Pipeline



---

## Repository Structure

```
aceest_cicd/
├── app.py                        # Flask REST API application
├── test_app.py                   # Pytest test suite (40+ test cases)
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Optimized Docker image definition
├── Jenkinsfile                   # Jenkins declarative pipeline
├── .github/
│   └── workflows/
│       └── main.yml              # GitHub Actions CI/CD workflow
└── README.md
```

---

## Application Overview

The Flask API exposes the following endpoints:

| Method | Endpoint                    | Description                        |
|--------|-----------------------------|------------------------------------|
| GET    | `/`                         | App status                         |
| GET    | `/health`                   | Health check                       |
| GET    | `/programs`                 | List all fitness programs          |
| POST   | `/calculate_calories`       | Calculate daily calorie target     |
| GET    | `/clients`                  | List all registered clients        |
| POST   | `/clients`                  | Register / update a client         |
| GET    | `/clients/<name>`           | Get a specific client              |
| POST   | `/progress`                 | Log weekly adherence progress      |
| GET    | `/progress/<name>`          | Fetch client progress history      |
| POST   | `/bmi`                      | Calculate BMI and category         |

**Fitness Programs supported:**
- **Fat Loss (FL)** — 22 kcal per kg body weight
- **Muscle Gain (MG)** — 35 kcal per kg body weight
- **Beginner (BG)** — 26 kcal per kg body weight

---

## Local Setup & Execution

### Prerequisites
- Python 3.11+
- Docker Desktop (for containerization)
- Git

### Step 1 — Clone the Repository

```bash
git clone https://github.com/<your-username>/aceest-cicd.git
cd aceest-cicd
```

### Step 2 — Create Virtual Environment & Install Dependencies

```bash
python -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

pip install -r requirements.txt
```

### Step 3 — Run the Flask Application Locally

```bash
python app.py
```

The server starts at `http://localhost:5000`.

**Quick test with curl:**
```bash
# Health check
curl http://localhost:5000/health

# Calculate calories
curl -X POST http://localhost:5000/calculate_calories \
  -H "Content-Type: application/json" \
  -d '{"weight_kg": 75, "program": "Muscle Gain (MG)"}'

# Add a client
curl -X POST http://localhost:5000/clients \
  -H "Content-Type: application/json" \
  -d '{"name":"Arjun","age":28,"weight_kg":75,"program":"Muscle Gain (MG)","adherence":80}'
```

---

## Running Tests Manually

### Run the full Pytest suite

```bash
pytest test_app.py -v
```

### Run with coverage report

```bash
pytest test_app.py -v --cov=app --cov-report=term-missing
```

### Run only a specific class

```bash
pytest test_app.py::TestCalorieCalculator -v
```

**Expected output:**
```
collected 40+ items

test_app.py::TestHealthEndpoints::test_index_returns_ok          PASSED
test_app.py::TestHealthEndpoints::test_health_returns_healthy     PASSED
test_app.py::TestCalorieCalculator::test_fat_loss_calories       PASSED
...
====== 40 passed in 0.35s ======
```

---

## Docker — Build & Run

### Build the Docker image

```bash
docker build -t aceest-fitness:latest .
```

### Run the container

```bash
docker run -d -p 5000:5000 --name aceest aceest-fitness:latest
```

### Test inside the container

```bash
# Run tests inside the container environment
docker run --rm aceest-fitness:latest \
  sh -c "pip install pytest pytest-cov && pytest test_app.py -v"
```

### Stop & remove the container

```bash
docker stop aceest && docker rm aceest
```

---

## GitHub Actions — CI/CD Pipeline

The pipeline is defined in `.github/workflows/main.yml` and is **automatically triggered** on every `push` or `pull_request` to the `main` branch.

### Pipeline Stages

```
Push to GitHub
      │
      ▼
┌─────────────┐
│  Job 1:     │  Checkout → Install deps → flake8 lint
│  LINT       │
└──────┬──────┘
       │ passes
       ▼
┌─────────────┐
│  Job 2:     │  docker build -t aceest-fitness:<sha> .
│  DOCKER     │
│  BUILD      │
└──────┬──────┘
       │ passes
       ▼
┌─────────────┐
│  Job 3:     │  pytest test_app.py -v --cov=app --cov-fail-under=80
│  TEST       │
└─────────────┘
```

### Viewing Results
#################

1. Go to your GitHub repository.
2. Click the **Actions** tab.
3. Click the latest workflow run to see per-job logs and the coverage artifact.

---

## Jenkins — BUILD Phase

The `Jenkinsfile` defines a **declarative pipeline** that Jenkins executes when it detects a new commit on GitHub.

### Jenkins Setup Steps

1. **Install Jenkins** (local or server):
   ```bash
   # Docker-based Jenkins (easiest)
   docker run -d -p 8080:8080 -p 50000:50000 \
     -v jenkins_home:/var/jenkins_home \
     jenkins/jenkins:lts
   ```

2. **Install required Jenkins plugins** via *Manage Jenkins → Plugin Manager*:
   - Git Plugin
   - Pipeline Plugin
   - Docker Pipeline Plugin
   - Coverage Report Plugin (optional)

3. **Create a new Pipeline project**:
   - New Item → Pipeline
   - Under *Pipeline*, select **Pipeline script from SCM**
   - SCM: Git → enter your GitHub repository URL
   - Script Path: `Jenkinsfile`

4. **Trigger a build**:
   - Click **Build Now**, or configure a **GitHub Webhook** to auto-trigger.

### Jenkins Pipeline Stages

| Stage              | What It Does                                             |
|--------------------|----------------------------------------------------------|
| Checkout           | Pulls latest code from GitHub via `checkout scm`         |
| Environment Setup  | Creates Python venv and installs `requirements.txt`      |
| Lint               | Runs `flake8` for syntax and style validation            |
| Unit Tests         | Executes `pytest` with coverage; produces `coverage.xml` |
| Docker Build       | Builds and tags the Docker image                         |
| Docker Verify      | Verifies the image and does a smoke-test import          |

On **success**, the workspace is cleaned and a ✅ message is printed.  
On **failure**, a ❌ message is printed with a pointer to the failing stage logs.

---

## Version History

| Version | File                  | Key Feature Added                            |
|---------|-----------------------|----------------------------------------------|
| 1.0     | Aceestver-1_0.py      | Base tkinter UI, program selector            |
| 1.1     | Aceestver-1_1.py      | Calorie calculator, progress slider          |
| 1.1.2   | Aceestver1_1_2.py     | Multi-client table, CSV export, charts       |
| 2.0.1   | Aceestver2_0_1.py     | SQLite persistence, load/save client         |
| 2.1.2   | Aceestver-2_1_2.py    | Progress logging to DB                       |
| 2.2.1   | Aceestver-2_2_1.py    | Matplotlib adherence chart                   |
| 2.2.4   | Aceestver-2_2_4.py    | Bug fixes and UI polish                      |
| 3.0.1   | Aceestver-3_0_1.py    | Role-based login, workouts tab               |
| 3.1.2   | Aceestver-3_1_2.py    | Metrics tracking, embedded charts            |
| 3.2.4   | Aceestver-3_2_4.py    | PDF report, AI program generator (full app)  |
| **API** | **app.py**            | **Flask REST API for CI/CD pipeline**        |

---



---

