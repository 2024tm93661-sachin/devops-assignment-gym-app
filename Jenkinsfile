// ─────────────────────────────────────────────────────────────────────────────
// ACEest Fitness & Gym — Jenkinsfile
// Declarative pipeline for the Jenkins BUILD phase.
// Pulls latest code from GitHub and performs a clean build + test.
// ─────────────────────────────────────────────────────────────────────────────

pipeline {
    agent any

    environment {
        IMAGE_NAME = "yourdockerhub/gym-app"
        TAG = "v1.${BUILD_NUMBER}"
    }

    stages {

        stage('Clone') {
            steps {
                git 'https://github.com/2024tm93661-sachin/devops-assignment-gym-app.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat 'python -m pip install -r requirements.txt'
            }
        }

        stage('Lint Check') {
            steps {
                bat 'flake8 .'
            }
        }

        stage('Run Tests') {
            steps {
                bat 'pytest --cov=app'
            }
        }

        stage('Build Docker Image') {
            steps {
                bat "docker build -t %IMAGE_NAME%:%TAG% ."
            }
        }

        stage('Push to DockerHub') {
            steps {
                withCredentials([string(credentialsId: 'dockerhub-password', variable: 'PASS')]) {
                    bat "docker login -u yourdockerhub -p %PASS%"
                    bat "docker push %IMAGE_NAME%:%TAG%"
                }
            }
        }

        stage('Deploy (Kubernetes)') {
            steps {
                bat "kubectl set image deployment/gym-app gym-app=%IMAGE_NAME%:%TAG%"
            }
        }

        stage('Rollback if Failed') {
            when {
                expression { currentBuild.result == 'FAILURE' }
            }
            steps {
                bat "kubectl rollout undo deployment/gym-app"
            }
        }
		stage('SonarQube Analysis') {
            steps {
                 sh 'sonar-scanner'
            }
}
    }
}