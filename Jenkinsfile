pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        skipDefaultCheckout(true)
    }

    parameters {
        choice(name: 'AI_MODE', choices: ['ADVISORY', 'ADAPTIVE'], description: 'ADVISORY logs risk; ADAPTIVE runs additional preflight for high-risk builds.')
        booleanParam(name: 'ENABLE_DEPLOY', defaultValue: false, description: 'Keep disabled during validation. Enable only after approval.')
    }

    environment {
        IMAGE_REPO = 'ghcr.io/2024tm93661-sachin/fitness-app'
        APP_SERVER = '172.31.18.175'
        AI_PROJECT = '/home/ubuntu/ai-cicd-optimization'
        AI_THRESHOLD = '0.50'
        IMAGE_TAG = "ai-candidate-${BUILD_NUMBER}"
        AI_RISK = 'UNKNOWN'
        AI_ROUTE = 'STANDARD'
    }

    stages {
        stage('Checkout Source') {
            steps {
                checkout scm
            }
        }

        stage('AI Risk Assessment') {
    steps {
        script {
            env.AI_RISK = 'UNKNOWN'
            env.AI_FAILURE_PROBABILITY = ''

            def aiStatus = sh(
                script: '''
                    set -eu

                    AI_DIR="/home/ubuntu/ai-cicd-optimization"
                    AI_PYTHON="$AI_DIR/.venv/bin/python"
                    AI_HISTORY="$AI_DIR/data/experimental_live_history.csv"

                    # Determine the cutoff from completed historical builds.
                    # This is separate from the current Jenkins job's build number.
                    HISTORY_CUTOFF="$(
                        "$AI_PYTHON" - "$AI_HISTORY" <<'PYCODE'
import csv
import sys

with open(sys.argv[1], newline="") as f:
    rows = list(csv.DictReader(f))

completed = [
    int(row["build_number"])
    for row in rows
    if row.get("actual_result") in ("SUCCESS", "FAILURE")
]

if not completed:
    raise SystemExit("No completed historical builds found")

print(max(completed) + 1)
PYCODE
                    )"

                    "$AI_PYTHON" "$AI_DIR/scripts/predict_pipeline_failure.py" \
                        --model "$AI_DIR/models/jenkins_failure_model.joblib" \
                        --history "$AI_HISTORY" \
                        --current-build "$HISTORY_CUTOFF" \
                        > ai_prediction.log 2>&1
                ''',
                returnStatus: true
            )

            if (aiStatus != 0) {
                echo "AI prediction unavailable (exit ${aiStatus}). Continuing mandatory CI/CD checks."
                writeFile file: 'ai_prediction.json', text: groovy.json.JsonOutput.toJson([
                    build_number: env.BUILD_NUMBER,
                    prediction_status: 'UNAVAILABLE',
                    prediction_mode: 'advisory_only'
                ])
            } else {
                def predictionLog = readFile('ai_prediction.log')
                echo predictionLog

                def matcher = predictionLog =~ /Estimated failure probability:\\s*([0-9]+(?:\\.[0-9]+)?)%/

                if (matcher.find()) {
                    def percentage = matcher.group(1).toDouble()
                    def probability = percentage / 100.0

                    env.AI_FAILURE_PROBABILITY = probability.toString()
                    env.AI_RISK = probability >= 0.5 ? 'HIGH' : 'LOW'

                    writeFile file: 'ai_prediction.json', text: groovy.json.JsonOutput.toJson([
                        build_number: env.BUILD_NUMBER,
                        predicted_failure_probability: probability,
                        predicted_failure: probability >= 0.5,
                        threshold: 0.5,
                        risk_level: env.AI_RISK,
                        prediction_status: 'SUCCESS',
                        prediction_mode: 'advisory_only',
                        history_source: 'experimental_live_history.csv'
                    ])

                    echo "AI risk classification: ${env.AI_RISK}"
                } else {
                    echo 'AI output could not be parsed. Continuing standard pipeline.'

                    writeFile file: 'ai_prediction.json', text: groovy.json.JsonOutput.toJson([
                        build_number: env.BUILD_NUMBER,
                        prediction_status: 'UNAVAILABLE',
                        prediction_mode: 'advisory_only'
                    ])
                }
            }
        }
    }
}

        stage('High-Risk Preflight') {
            when { expression { env.AI_ROUTE == 'HIGH_RISK_PREFLIGHT' } }
            steps {
                sh '''#!/bin/bash
set -euo pipefail
# Lightweight checks; do not install dependencies or skip subsequent tests.
python3 -m compileall -q .
docker info >/dev/null
[ -s requirements.txt ]
'''
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
'''
            }
        }

        stage('Automated Tests') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail
. .venv/bin/activate
python -m pytest -v
'''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail
docker build -t "$IMAGE_REPO:$IMAGE_TAG" .
'''
            }
        }

        stage('Push Image to GHCR') {
            when { expression { params.ENABLE_DEPLOY } }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'github-container-registry',
                    usernameVariable: 'GHCR_USER',
                    passwordVariable: 'GHCR_TOKEN'
                )]) {
                    sh '''#!/bin/bash
set -euo pipefail
export DOCKER_CONFIG="$(mktemp -d)"
trap 'rm -rf "$DOCKER_CONFIG"' EXIT
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
docker push "$IMAGE_REPO:$IMAGE_TAG"
'''
                }
            }
        }

        stage('Deploy to EC2-2') {
            when { expression { params.ENABLE_DEPLOY } }
            steps {
                sshagent(credentials: ['aws-appserver-ssh']) {
                    sh '''#!/bin/bash
set -euo pipefail
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes \
    "ubuntu@$APP_SERVER" "bash -s -- '$IMAGE_TAG'" <<'REMOTE'
set -eu
VERSION="$1"
IMAGE="ghcr.io/2024tm93661-sachin/fitness-app:$VERSION"
echo "Pulling $IMAGE"
docker pull "$IMAGE"
OLD_IMAGE="$(docker inspect fitness-app --format '{{.Config.Image}}' 2>/dev/null || true)"
echo 'Replacing fitness-app container'
docker rm -f fitness-app 2>/dev/null || true
docker run -d --name fitness-app --restart unless-stopped -p 5000:5000 "$IMAGE"
healthy=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fsS http://localhost:5000/health >/dev/null; then
        healthy=1
        break
    fi
    sleep 3
done
if [ "$healthy" -ne 1 ]; then
    echo 'New container failed its health check'
    docker logs --tail 50 fitness-app || true
    docker rm -f fitness-app || true
    if [ -n "$OLD_IMAGE" ]; then
        echo "Attempting rollback to $OLD_IMAGE"
        docker run -d --name fitness-app --restart unless-stopped -p 5000:5000 "$OLD_IMAGE" || true
    fi
    exit 1
fi
echo "Deployment successful: $IMAGE"
REMOTE
'''
                }
            }
        }
    }

    post {
        success {
            echo "SUCCESS: AI route=${env.AI_ROUTE}; image=${env.IMAGE_REPO}:${env.IMAGE_TAG}; deploy enabled=${params.ENABLE_DEPLOY}"
        }
        failure {
            echo 'FAILED: Check Console Output and failing stage.'
        }
        always {
            archiveArtifacts artifacts: 'ai_prediction.log,ai_prediction.json', allowEmptyArchive: true
            sh 'rm -rf .venv || true'
        }
    }
}

