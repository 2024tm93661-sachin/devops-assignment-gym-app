// ─────────────────────────────────────────────────────────────────────────────
// ACEest Fitness & Gym — Jenkinsfile
// Declarative pipeline for the Jenkins BUILD phase.
// Pulls latest code from GitHub and performs a clean build + test.
// ─────────────────────────────────────────────────────────────────────────────

pipeline {
    agent any
    
    tools {
    git 'Default'
    }
    environment {
        IMAGE_NAME = "aceest-fitness"
        IMAGE_TAG  = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Environment Setup') {
            steps {
                bat '''
                    python -m venv venv
                    call venv\\Scripts\\activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                bat '''
                    call venv\\Scripts\\activate
                    flake8 app.py --max-line-length=120 --statistics
                    flake8 . || exit 0
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                bat '''
                    call venv\\Scripts\\activate
                    pytest test_app.py -v --tb=short --junitxml=test-results.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: '**/test-results.xml'
                }
            }
        }

        stage('Docker Build') {
            steps {
                bat "docker build -t %IMAGE_NAME%:%IMAGE_TAG% ."
                bat "docker tag %IMAGE_NAME%:%IMAGE_TAG% %IMAGE_NAME%:latest"
            }
        }

        stage('Docker Verify') {
            steps {
                bat "docker images %IMAGE_NAME%"
                bat "docker run --rm %IMAGE_NAME%:latest python -c \"import app; print('App import OK')\""
            }
        }
    }

    post {
        success { echo '✅ BUILD SUCCESS' }
        failure { echo '❌ BUILD FAILED' }
        always {
            bat "docker rmi %IMAGE_NAME%:%IMAGE_TAG% || exit 0"
            cleanWs()
        }
    }
}
