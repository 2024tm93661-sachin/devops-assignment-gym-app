
stage('Deploy to EC2-2') {
    steps {
        sshagent(credentials: ['aws-appserver-ssh']) {
            sh '''
                set -eu

                echo "Deploying image version: $BUILD_NUMBER"

                ssh -o BatchMode=yes \
                    -o StrictHostKeyChecking=yes \
                    ubuntu@172.31.18.175 \
                    "bash -s -- '$BUILD_NUMBER'" <<'REMOTE'
set -eu

VERSION="$1"
IMAGE="ghcr.io/2024tm93661-sachin/fitness-app:$VERSION"

echo "Pulling Docker image: $IMAGE"
docker pull "$IMAGE"

echo "Replacing existing container"
docker rm -f fitness-app 2>/dev/null || true

docker run -d \
    --name fitness-app \
    --restart unless-stopped \
    -p 5000:5000 \
    "$IMAGE"

echo "Checking Flask application health"

HEALTHY=0

for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fsS http://localhost:5000/health; then
        HEALTHY=1
        break
    fi

    sleep 3
done

if [ "$HEALTHY" -ne 1 ]; then
    echo "ERROR: Application failed health check"
    docker logs --tail 50 fitness-app
    exit 1
fi

echo "Deployment successful"
REMOTE
            '''
        }
    }
}
