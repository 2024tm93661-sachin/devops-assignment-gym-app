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
                    // Predictor uses only completed history, never this build's outcome.
                    // Keep model and training files fixed during evaluation.
                    int currentBuildNumber = env.BUILD_NUMBER as Integer
                    String prediction = sh(
                        script: '''#!/bin/bash
set -euo pipefail
"$AI_PROJECT/.venv/bin/python" "$AI_PROJECT/scripts/predict_pipeline_failure.py" \
  --model "$AI_PROJECT/models/jenkins_failure_model.joblib" \
  --history "$AI_PROJECT/data/experimental_live_history.csv" \
  --current-build "$BUILD_NUMBER"
''',
                        returnStdout: true
                    ).trim()
                    echo prediction
                    writeFile file: 'ai_prediction.log', text: prediction + '\n'

                    // Match the predictor's existing human-readable percentage output.
                    def match = (prediction =~ /(?i)(?:failure\s*(?:risk|probability)|predicted\s*failure\s*probability)\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*%/)
                    if (!match.find()) {
                        error('AI prediction percentage not found in predictor output. Review ai_prediction.log; no deployment will occur.')
                    }
                    double probability = (match.group(1) as Double) / 100.0
                    if (probability < 0.0 || probability > 1.0) {
                        error('Invalid AI failure probability')
                    }
                    env.AI_RISK = String.format(java.util.Locale.US, '%.4f', probability)
                    env.AI_ROUTE = (params.AI_MODE == 'ADAPTIVE' && probability >= (env.AI_THRESHOLD as Double)) ? 'HIGH_RISK_PREFLIGHT' : 'STANDARD'
                    writeFile file: 'ai_prediction.json', text: groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson([
                        build_number: currentBuildNumber,
                        predicted_failure_probability: probability,
                        threshold: env.AI_THRESHOLD as Double,
                        model_version: 'initial_logistic_regression',
                        ai_mode: params.AI_MODE,
                        selected_route: env.AI_ROUTE,
                        prediction_mode: 'advisory_or_adaptive',
                    ])) + '\n'
                    echo "AI selected route: ${env.AI_ROUTE}"
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
