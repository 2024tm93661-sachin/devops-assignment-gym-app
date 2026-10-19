pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        IMAGE_REPO = 'ghcr.io/2024tm93661-sachin/fitness-app'
        APP_SERVER = '172.31.18.175'
    }

    stages {
        stage('Checkout Source') {
            steps {
                checkout scm
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
                    docker build -t "$IMAGE_REPO:$BUILD_NUMBER" .
                '''
            }
        }

        stage('Push Image to GHCR') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'github-container-registry',
                    usernameVariable: 'GHCR_USER',
                    passwordVariable: 'GHCR_TOKEN'
                )]) {
                    sh '''
                        set -eu
                        export DOCKER_CONFIG="$(mktemp -d)"
                        trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                        printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
                        docker push "$IMAGE_REPO:$BUILD_NUMBER"
                    '''
                }
            }
        }

        stage('Deploy to EC2-2') {
            steps {
                sshagent(credentials: ['aws-appserver-ssh']) {
                    sh '''
                        set -eu
                        ssh -o BatchMode=yes -o StrictHostKeyChecking=yes \
                            "ubuntu@$APP_SERVER" "bash -s -- '$BUILD_NUMBER'" <<'REMOTE'
set -eu

VERSION="$1"
IMAGE="ghcr.io/2024tm93661-sachin/fitness-app:$VERSION"

# The ubuntu account on EC2-2 must already be able to pull private GHCR images.
echo "Pulling $IMAGE"
docker pull "$IMAGE"

# Remember the old image to allow a basic rollback on a failed health check.
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
            echo "SUCCESS: Tested, published, and deployed ${env.IMAGE_REPO}:${env.BUILD_NUMBER}"
        }
        failure {
            echo 'FAILED: Open Console Output and inspect the failing stage.'
        }
        always {
            sh 'rm -rf .venv || true'
        }
    }
}
