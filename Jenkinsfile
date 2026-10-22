@NonCPS
String extractFailurePercentage(String logText) {
    def matcher = logText =~ /Estimated failure probability:\s*([0-9]+(?:\.[0-9]+)?)%/
    return matcher.find() ? matcher.group(1) : null
}

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        skipDefaultCheckout(true)
    }

    parameters {
        choice(name: 'AI_MODE', choices: ['ADVISORY', 'ADAPTIVE'], description: 'ADAPTIVE adds a lightweight preflight for high-risk predictions.')
        booleanParam(name: 'ENABLE_DEPLOY', defaultValue: false, description: 'Push image to GHCR and deploy to EC2-2 only when enabled.')
    }

    environment {
        IMAGE_REPO = 'ghcr.io/2024tm93661-sachin/fitness-app'
        APP_SERVER = '172.31.18.175'
        AI_DIR = '/home/ubuntu/ai-cicd-optimization'
        AI_RISK = 'UNKNOWN'
        AI_FAILURE_PROBABILITY = ''
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
                    int aiStatus = sh(
                        script: '''
                            set -eu
                            AI_PYTHON="$AI_DIR/.venv/bin/python"
                            AI_HISTORY="$AI_DIR/data/experimental_live_history.csv"

                            # Determine a cutoff using the experimental history's own numbering.
                            # Do not confuse this with the new Jenkins job's BUILD_NUMBER.
                            HISTORY_CUTOFF="$("$AI_PYTHON" - "$AI_HISTORY" <<'PYCODE'
import csv
import sys

with open(sys.argv[1], newline='') as f:
    rows = list(csv.DictReader(f))

numbers = []
for row in rows:
    result = (row.get('actual_result') or row.get('result') or '').strip().upper()
    if result in ('SUCCESS', 'FAILURE'):
        try:
            numbers.append(int(row['build_number']))
        except (KeyError, ValueError, TypeError):
            pass

if not numbers:
    raise SystemExit('No completed historical builds available')

print(max(numbers) + 1)
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
                        echo "AI prediction unavailable (exit ${aiStatus}); mandatory CI/CD checks will continue."
                        if (fileExists('ai_prediction.log')) {
                            echo readFile('ai_prediction.log')
                        }
                        writeFile file: 'ai_prediction.json', text: groovy.json.JsonOutput.toJson([
                            build_number: env.BUILD_NUMBER,
                            prediction_status: 'UNAVAILABLE',
                            prediction_mode: 'advisory_only'
                        ])
                    } else {
                        String predictionLog = readFile('ai_prediction.log')
                        echo predictionLog
                        String percentageText = extractFailurePercentage(predictionLog)

                        if (percentageText != null) {
                            double probability = percentageText.toDouble() / 100.0d
                            env.AI_FAILURE_PROBABILITY = probability.toString()
                            env.AI_RISK = probability >= 0.5d ? 'HIGH' : 'LOW'

                            writeFile file: 'ai_prediction.json', text: groovy.json.JsonOutput.toJson([
                                build_number: env.BUILD_NUMBER,
                                predicted_failure_probability: probability,
                                predicted_failure: probability >= 0.5d,
                                threshold: 0.5,
                                risk_level: env.AI_RISK,
                                prediction_status: 'SUCCESS',
                                prediction_mode: 'advisory_only',
                                history_source: 'experimental_live_history.csv'
                            ])
                            echo "AI risk classification: ${env.AI_RISK}"
                        } else {
                            echo 'AI prediction output could not be parsed; continuing mandatory checks.'
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
            when {
                expression { params.AI_MODE == 'ADAPTIVE' && env.AI_RISK == 'HIGH' }
            }
            steps {
                sh '''
                    set -eu
                    echo 'High-risk preflight: checking Python, Docker daemon and required source files.'
                    python3 --version
                    docker version >/dev/null
                    test -f requirements.txt
                    test -f Dockerfile
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    set -eu
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
                sh '''
                    set -eu
                    . .venv/bin/activate
                    python -m pytest -v
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu
                    IMAGE_TAG="ai-candidate-${BUILD_NUMBER}"
                    docker build -t "${IMAGE_REPO}:${IMAGE_TAG}" .
                '''
            }
        }

        stage('Push Image to GHCR') {
            when { expression { return params.ENABLE_DEPLOY } }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'github-container-registry',
                    usernameVariable: 'GHCR_USER',
                    passwordVariable: 'GHCR_TOKEN'
                )]) {
                    sh '''
                        set -eu
                        IMAGE_TAG="ai-candidate-${BUILD_NUMBER}"
                        export DOCKER_CONFIG="$(mktemp -d)"
                        trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                        printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
                        docker push "${IMAGE_REPO}:${IMAGE_TAG}"
                    '''
                }
            }
        }

        stage('Deploy to EC2-2') {
            when { expression { return params.ENABLE_DEPLOY } }
            steps {
                sshagent(credentials: ['aws-appserver-ssh']) {
                    sh '''
                        set -eu
                        IMAGE_TAG="ai-candidate-${BUILD_NUMBER}"
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
            echo "SUCCESS: Tests and Docker build completed for ${env.IMAGE_REPO}:ai-candidate-${env.BUILD_NUMBER}. Deployment enabled: ${params.ENABLE_DEPLOY}"
        }
        failure {
            echo 'FAILED: Check Console Output and the failing stage.'
        }
        always {
            archiveArtifacts artifacts: 'ai_prediction.json,ai_prediction.log', allowEmptyArchive: true
            sh 'rm -rf .venv || true'
        }
    }
}
