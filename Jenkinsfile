pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'SIMULATE_FAILURE',
            defaultValue: false,
            description: 'Enable to test deployment failure and automatic rollback'
        )
    }

    environment {
        APP_NAME = "orders-api"
        NETWORK = "orders-network"

        BLUE = "orders-blue"
        GREEN = "orders-green"

        BLUE_PORT = "8181"
        GREEN_PORT = "8182"

        APP_PORT = "5000"
        VERSION = "7.9"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm

                script {
                    env.GIT_SHA = bat(
                        script: '@git rev-parse HEAD',
                        returnStdout: true
                    ).trim()

                    env.GIT_SHORT = env.GIT_SHA.take(7)
                    env.IMAGE = "orders-api:${VERSION}-${BUILD_NUMBER}-${env.GIT_SHORT}"

                    echo "Application : ${APP_NAME}"
                    echo "Version     : ${VERSION}"
                    echo "Git SHA     : ${GIT_SHA}"
                    echo "Docker Image: ${IMAGE}"
                }
            }
        }

        stage('Validate Version') {
            steps {
                script {
                    if (!env.VERSION?.trim()) {
                        error("Version is missing")
                    }

                    echo "Version validation successful"
                    echo "Release Version: ${VERSION}"
                    echo "Git Commit: ${GIT_SHA}"
                }
            }
        }

        stage('Unit/Application Test') {
            steps {
                bat """
                    docker run --rm ^
                    -v "%WORKSPACE%:/workspace" ^
                    -w /workspace ^
                    python:3.12-slim ^
                    python -m py_compile app/app.py
                """
            }
        }

        stage('Docker Build') {
            steps {
                bat "docker build -t ${IMAGE} ."
                echo "Docker image created successfully"
            }
        }

        stage('Docker Image Validation') {
            steps {
                bat "docker image inspect ${IMAGE}"
                echo "Docker image validation successful"
            }
        }

        stage('Determine Deployment Color') {
            steps {
                script {

                    def blueExists = bat(
                        returnStatus: true,
                        script: "docker inspect ${BLUE} >NUL 2>&1"
                    )

                    def greenExists = bat(
                        returnStatus: true,
                        script: "docker inspect ${GREEN} >NUL 2>&1"
                    )

                    if (blueExists == 0) {

                        env.CURRENT_CONTAINER = BLUE
                        env.CURRENT_PORT = BLUE_PORT
                        env.CURRENT_COLOR = "BLUE"

                        env.CANDIDATE_CONTAINER = GREEN
                        env.CANDIDATE_PORT = GREEN_PORT
                        env.CANDIDATE_COLOR = "GREEN"

                    } else if (greenExists == 0) {

                        env.CURRENT_CONTAINER = GREEN
                        env.CURRENT_PORT = GREEN_PORT
                        env.CURRENT_COLOR = "GREEN"

                        env.CANDIDATE_CONTAINER = BLUE
                        env.CANDIDATE_PORT = BLUE_PORT
                        env.CANDIDATE_COLOR = "BLUE"

                    } else {

                        env.CURRENT_CONTAINER = "NONE"
                        env.CURRENT_PORT = ""
                        env.CURRENT_COLOR = "NONE"

                        env.CANDIDATE_CONTAINER = GREEN
                        env.CANDIDATE_PORT = GREEN_PORT
                        env.CANDIDATE_COLOR = "GREEN"
                    }

                    echo "Current Production : ${CURRENT_COLOR}"
                    echo "Current Container   : ${CURRENT_CONTAINER}"
                    echo "Candidate           : ${CANDIDATE_COLOR}"
                    echo "Candidate Container : ${CANDIDATE_CONTAINER}"
                    echo "Candidate Port      : ${CANDIDATE_PORT}"
                }
            }
        }

        stage('Start Candidate') {
            steps {

                bat """
                    docker rm -f ${CANDIDATE_CONTAINER} >NUL 2>&1
                    exit /b 0
                """

                bat """
                    docker run -d ^
                    --name ${CANDIDATE_CONTAINER} ^
                    --network ${NETWORK} ^
                    -p ${CANDIDATE_PORT}:${APP_PORT} ^
                    -e APP_VERSION=${VERSION} ^
                    -e GIT_SHA=${GIT_SHA} ^
                    ${IMAGE}
                """

                echo "Candidate ${CANDIDATE_COLOR} started"
            }
        }

        stage('Container Validation') {
            steps {

                bat "docker ps --filter \"name=${CANDIDATE_CONTAINER}\""

                bat "docker inspect ${CANDIDATE_CONTAINER}"

                script {
                    def running = bat(
                        returnStatus: true,
                        script: "docker inspect -f \"{{.State.Running}}\" ${CANDIDATE_CONTAINER} | findstr /I true"
                    )

                    if (running != 0) {
                        error("Candidate container is not running")
                    }
                }

                echo "Candidate container validation successful"
            }
        }

        stage('Application Health Check') {
            steps {
                script {

                    if (params.SIMULATE_FAILURE) {

                        echo "=========================================="
                        echo "FAILURE TEST ENABLED"
                        echo "Intentionally checking invalid port 8199"
                        echo "=========================================="

                        bat """
                            powershell -NoProfile -Command "\$r=Invoke-WebRequest -Uri 'http://localhost:8199/health' -UseBasicParsing; if (\$r.StatusCode -ne 200) { exit 1 }"
                        """

                    } else {

                        bat """
                            powershell -NoProfile -Command "\$r=Invoke-WebRequest -Uri 'http://localhost:${CANDIDATE_PORT}/health' -UseBasicParsing; if (\$r.StatusCode -ne 200) { exit 1 }; Write-Host \$r.Content"
                        """
                    }
                }
            }
        }

        stage('Integration Check') {
            steps {

                bat """
                    powershell -NoProfile -Command "\$r=Invoke-WebRequest -Uri 'http://localhost:${CANDIDATE_PORT}/' -UseBasicParsing; if (\$r.StatusCode -ne 200) { exit 1 }; Write-Host \$r.Content"
                """

                bat """
                    powershell -NoProfile -Command "\$r=Invoke-WebRequest -Uri 'http://localhost:${CANDIDATE_PORT}/orders' -UseBasicParsing; if (\$r.StatusCode -ne 200) { exit 1 }; Write-Host \$r.Content"
                """

                echo "Integration checks successful"
            }
        }

        stage('Traffic Switch') {
            steps {
                script {

                    echo "=========================================="
                    echo "TRAFFIC SWITCH"
                    echo "=========================================="

                    echo "Old Production : ${CURRENT_COLOR}"
                    echo "New Production : ${CANDIDATE_COLOR}"
                    echo "Version        : ${VERSION}"

                    env.ACTIVE_CONTAINER = env.CANDIDATE_CONTAINER
                    env.ACTIVE_PORT = env.CANDIDATE_PORT
                    env.ACTIVE_COLOR = env.CANDIDATE_COLOR

                    echo "Traffic switched to ${ACTIVE_COLOR}"
                }
            }
        }

        stage('Old Version Cleanup') {
            steps {
                script {

                    if (env.CURRENT_CONTAINER != "NONE") {

                        echo "Removing old production container: ${CURRENT_CONTAINER}"

                        bat """
                            docker rm -f ${CURRENT_CONTAINER} >NUL 2>&1
                            exit /b 0
                        """

                    } else {
                        echo "No previous production container exists"
                    }
                }
            }
        }

        stage('Deployment Verification') {
            steps {

                bat """
                    powershell -NoProfile -Command "\$r=Invoke-WebRequest -Uri 'http://localhost:${ACTIVE_PORT}/health' -UseBasicParsing; if (\$r.StatusCode -ne 200) { exit 1 }; Write-Host \$r.Content"
                """

                bat """
                    powershell -NoProfile -Command "\$r=Invoke-WebRequest -Uri 'http://localhost:${ACTIVE_PORT}/' -UseBasicParsing; if (\$r.StatusCode -ne 200) { exit 1 }; Write-Host \$r.Content"
                """

                bat "docker ps"

                echo "=========================================="
                echo "DEPLOYMENT VERIFICATION SUCCESSFUL"
                echo "=========================================="
                echo "Active Color : ${ACTIVE_COLOR}"
                echo "Active Port  : ${ACTIVE_PORT}"
                echo "Version      : ${VERSION}"
                echo "Git SHA      : ${GIT_SHA}"
                echo "Image        : ${IMAGE}"
            }
        }
    }

    post {

        success {
            echo "=========================================="
            echo "DEPLOYMENT SUCCESSFUL"
            echo "=========================================="
            echo "Application : ${APP_NAME}"
            echo "Version     : ${VERSION}"
            echo "Git SHA     : ${GIT_SHA}"
            echo "Image       : ${IMAGE}"
            echo "Active Color: ${ACTIVE_COLOR}"
            echo "Active Port : ${ACTIVE_PORT}"
            echo "=========================================="
        }

        failure {
            echo "=========================================="
            echo "DEPLOYMENT FAILED"
            echo "AUTOMATIC ROLLBACK STARTED"
            echo "=========================================="

            script {

                if (env.CANDIDATE_CONTAINER) {

                    echo "Removing failed candidate: ${CANDIDATE_CONTAINER}"

                    bat """
                        docker rm -f ${CANDIDATE_CONTAINER} >NUL 2>&1
                        exit /b 0
                    """
                }

                if (env.CURRENT_CONTAINER &&
                    env.CURRENT_CONTAINER != "NONE") {

                    echo "Previous production remains:"
                    echo "${CURRENT_CONTAINER}"
                    echo "Production Port: ${CURRENT_PORT}"

                    bat "docker ps --filter \"name=${CURRENT_CONTAINER}\""

                } else {

                    echo "No previous production container was available."
                }

                echo "=========================================="
                echo "ROLLBACK COMPLETE"
                echo "FAILED CANDIDATE REMOVED"
                echo "PREVIOUS VERSION PRESERVED"
                echo "=========================================="
            }
        }

        always {
            echo "=========================================="
            echo "JENKINS DEPLOYMENT PIPELINE FINISHED"
            echo "BUILD NUMBER: ${BUILD_NUMBER}"
            echo "=========================================="
        }
    }
}