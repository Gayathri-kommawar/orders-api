pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'SIMULATE_FAILURE',
            defaultValue: false,
            description: 'Set TRUE only to test health-check failure and rollback'
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

        // ============================================================
        // 1. CHECKOUT
        // ============================================================

        stage('Checkout') {
            steps {
                checkout scm

                script {
                    env.GIT_SHA = bat(
                        script: '@git rev-parse HEAD',
                        returnStdout: true
                    ).trim()

                    env.GIT_SHORT = env.GIT_SHA.take(7)

                    env.IMAGE = "orders-api:${VERSION}-${BUILD_NUMBER}-${GIT_SHORT}"

                    echo "Application : ${APP_NAME}"
                    echo "Version     : ${VERSION}"
                    echo "Git SHA     : ${GIT_SHA}"
                    echo "Docker Image: ${IMAGE}"
                }
            }
        }

        // ============================================================
        // 2. VALIDATE VERSION
        // ============================================================

        stage('Validate Version') {
            steps {
                script {
                    if (!env.VERSION?.trim()) {
                        error("Application version is missing")
                    }

                    echo "Version validation successful"
                    echo "Release Version: ${VERSION}"
                    echo "Git Commit     : ${GIT_SHA}"
                }
            }
        }

        // ============================================================
        // 3. UNIT / APPLICATION TEST
        // ============================================================
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
        

        // ============================================================
        // 4. DOCKER BUILD
        // ============================================================

        stage('Docker Build') {
            steps {
                bat """
                    docker build -t ${IMAGE} .
                """

                echo "Docker image created successfully"
            }
        }

        // ============================================================
        // 5. DOCKER IMAGE VALIDATION
        // ============================================================

        stage('Docker Image Validation') {
            steps {
                bat """
                    docker image inspect ${IMAGE}
                """

                echo "Docker image validation successful"
            }
        }

        // ============================================================
        // 6. DETERMINE BLUE / GREEN
        // ============================================================

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

                    /*
                     * If BLUE is running:
                     *     BLUE  = current production
                     *     GREEN = candidate
                     *
                     * If GREEN is running:
                     *     GREEN = current production
                     *     BLUE  = candidate
                     *
                     * If neither exists:
                     *     GREEN becomes first candidate
                     */

                    if (blueExists == 0) {

                        env.CURRENT_CONTAINER = BLUE
                        env.CURRENT_PORT = BLUE_PORT

                        env.CANDIDATE_CONTAINER = GREEN
                        env.CANDIDATE_PORT = GREEN_PORT

                        env.CURRENT_COLOR = "BLUE"
                        env.CANDIDATE_COLOR = "GREEN"

                    } else if (greenExists == 0) {

                        env.CURRENT_CONTAINER = GREEN
                        env.CURRENT_PORT = GREEN_PORT

                        env.CANDIDATE_CONTAINER = BLUE
                        env.CANDIDATE_PORT = BLUE_PORT

                        env.CURRENT_COLOR = "GREEN"
                        env.CANDIDATE_COLOR = "BLUE"

                    } else {

                        env.CURRENT_CONTAINER = "NONE"
                        env.CURRENT_PORT = ""

                        env.CANDIDATE_CONTAINER = GREEN
                        env.CANDIDATE_PORT = GREEN_PORT

                        env.CURRENT_COLOR = "NONE"
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

        // ============================================================
        // 7. START CANDIDATE
        // ============================================================

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

        // ============================================================
        // 8. CONTAINER VALIDATION
        // ============================================================

        stage('Container Validation') {
            steps {
                bat """
                    docker ps --filter "name=${CANDIDATE_CONTAINER}"
                """

                bat """
                    docker inspect ${CANDIDATE_CONTAINER}
                """

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

        // ============================================================
        // 9. APPLICATION HEALTH CHECK
        // ============================================================

        stage('Application Health Check') {
            steps {
                script {

                    if (params.SIMULATE_FAILURE) {

                        echo "FAILURE TEST ENABLED"
                        echo "Health check will intentionally use an invalid port"

                        bat """
                            powershell -NoProfile -Command ^
                            "\$r=Invoke-WebRequest http://localhost:8199/health -UseBasicParsing; ^
                            if (\$r.StatusCode -ne 200) { exit 1 }"
                        """

                    } else {

                        bat """
                            powershell -NoProfile -Command ^
                            "\$r=Invoke-WebRequest http://localhost:${CANDIDATE_PORT}/health -UseBasicParsing; ^
                            if (\$r.StatusCode -ne 200) { exit 1 }; ^
                            Write-Host \$r.Content"
                        """
                    }
                }
            }
        }

        // ============================================================
        // 10. INTEGRATION CHECK
        // ============================================================

        stage('Integration Check') {
            steps {

                bat """
                    powershell -NoProfile -Command ^
                    "\$r=Invoke-WebRequest http://localhost:${CANDIDATE_PORT}/ -UseBasicParsing; ^
                    if (\$r.StatusCode -ne 200) { exit 1 }; ^
                    Write-Host \$r.Content"
                """

                bat """
                    powershell -NoProfile -Command ^
                    "\$r=Invoke-WebRequest http://localhost:${CANDIDATE_PORT}/orders -UseBasicParsing; ^
                    if (\$r.StatusCode -ne 200) { exit 1 }; ^
                    Write-Host \$r.Content"
                """

                echo "Integration checks successful"
            }
        }

        // ============================================================
        // 11. TRAFFIC SWITCH
        // ============================================================

        stage('Traffic Switch') {
            steps {
                script {

                    echo "=========================================="
                    echo "TRAFFIC SWITCH"
                    echo "=========================================="

                    echo "Old Production : ${CURRENT_COLOR}"
                    echo "New Production : ${CANDIDATE_COLOR}"
                    echo "New Version    : ${VERSION}"
                    echo "New Port       : ${CANDIDATE_PORT}"

                    /*
                     * Simplified blue-green traffic switch.
                     *
                     * The validated candidate becomes the active
                     * production container.
                     */

                    env.ACTIVE_CONTAINER = env.CANDIDATE_CONTAINER
                    env.ACTIVE_PORT = env.CANDIDATE_PORT
                    env.ACTIVE_COLOR = env.CANDIDATE_COLOR

                    echo "Traffic switched to ${ACTIVE_COLOR}"
                }
            }
        }

        // ============================================================
        // 12. OLD VERSION CLEANUP
        // ============================================================

        stage('Old Version Cleanup') {
            steps {
                script {

                    if (env.CURRENT_CONTAINER != "NONE") {

                        echo "Removing old production container:"
                        echo "${CURRENT_CONTAINER}"

                        bat """
                            docker rm -f ${CURRENT_CONTAINER} >NUL 2>&1
                            exit /b 0
                        """

                    } else {

                        echo "No previous production container exists."
                    }
                }
            }
        }

        // ============================================================
        // 13. DEPLOYMENT VERIFICATION
        // ============================================================

        stage('Deployment Verification') {
            steps {

                bat """
                    powershell -NoProfile -Command ^
                    "\$r=Invoke-WebRequest http://localhost:${ACTIVE_PORT}/health -UseBasicParsing; ^
                    if (\$r.StatusCode -ne 200) { exit 1 }; ^
                    Write-Host \$r.Content"
                """

                bat """
                    powershell -NoProfile -Command ^
                    "\$r=Invoke-WebRequest http://localhost:${ACTIVE_PORT}/ -UseBasicParsing; ^
                    if (\$r.StatusCode -ne 200) { exit 1 }; ^
                    Write-Host \$r.Content"
                """

                bat """
                    docker ps
                """

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

    // ================================================================
    // POST BUILD
    // ================================================================

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
            echo "ROLLBACK STARTED"
            echo "=========================================="

            script {

                /*
                 * Remove only the failed candidate.
                 *
                 * The current production container is NOT removed.
                 */

                if (env.CANDIDATE_CONTAINER) {

                    echo "Removing failed candidate:"
                    echo "${CANDIDATE_CONTAINER}"

                    bat """
                        docker rm -f ${CANDIDATE_CONTAINER} >NUL 2>&1
                        exit /b 0
                    """
                }

                echo "=========================================="
                echo "ROLLBACK COMPLETE"
                echo "=========================================="

                if (env.CURRENT_CONTAINER &&
                    env.CURRENT_CONTAINER != "NONE") {

                    echo "Previous production remains:"
                    echo "${CURRENT_CONTAINER}"
                    echo "Production Port: ${CURRENT_PORT}"

                    bat """
                        docker ps --filter "name=${CURRENT_CONTAINER}"
                    """

                    bat """
                        powershell -NoProfile -Command ^
                        "\$r=Invoke-WebRequest http://localhost:${CURRENT_PORT}/health -UseBasicParsing; ^
                        if (\$r.StatusCode -ne 200) { exit 1 }; ^
                        Write-Host 'Previous production is healthy'"
                    """

                } else {

                    echo "No previous production container was available."
                }
            }

            echo "=========================================="
            echo "FAILED CANDIDATE REMOVED"
            echo "PREVIOUS VERSION PRESERVED"
            echo "=========================================="
        }

        always {
            echo "=========================================="
            echo "JENKINS DEPLOYMENT PIPELINE FINISHED"
            echo "Build Number: ${BUILD_NUMBER}"
            echo "=========================================="
        }
    }
}