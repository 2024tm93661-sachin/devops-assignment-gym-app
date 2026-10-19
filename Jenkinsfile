
pipeline {
    agent any

    stages {
        stage('Deploy to EC2-2') {
            steps {
                sshagent(credentials: ['aws-appserver-ssh']) {
                    sh '''
                        ssh -o BatchMode=yes \
                            -o StrictHostKeyChecking=yes \
                            ubuntu@172.31.18.175 \
                            'bash -s' <<'REMOTE'
set -eu

IMAGE="ghcr.io/2024tm93661-sachin/fitness-app:2"

echo "Pulling Docker image..."
docker pull "$IMAGE"

echo "Stopping old container..."
docker rm -f fitness-app 2>/dev/null || true

echo "Starting new container..."
docker run -d \
    --name fitness-app \
    --restart unless-stopped \
    -p 5000:5000 \
    "$IMAGE"

echo "Checking Flask health endpoint..."

HEALTHY=0

for attempt in 1 2 3 4 5 6 7 8 9 10
do
    if curl -fsS http://localhost:5000/health
    then
        HEALTHY=1
        break
    fi

    sleep 3
done

if [ "$HEALTHY" -ne 1 ]
then
    echo "ERROR: Health check failed"
    docker logs --tail 50 fitness-app
    exit 1
fi

echo "Deployment successful!"
REMOTE
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'AWS EC2 deployment completed successfully.'
        }

        failure {
            echo 'AWS EC2 deployment failed.'
        }
    }
}
