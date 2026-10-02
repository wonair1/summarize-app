pipeline {
  agent {
    kubernetes {
      yaml '''
apiVersion: v1
kind: Pod
spec:
  hostAliases:
  - ip: "172.16.0.200"
    hostnames: ["myregistry.com", "mygitlab.com"]
  containers:
  - name: dind
    image: docker:dind
    securityContext:
      privileged: true
    env:
    - name: DOCKER_TLS_CERTDIR
      value: ""
    args: ["--insecure-registry=myregistry.com"]
    resources:
      requests:
        memory: "1Gi"
      limits:
        memory: "3Gi"
    volumeMounts:
    - name: docker-data
      mountPath: /var/lib/docker
  volumes:
  - name: docker-data
    emptyDir: {}
'''
    }
  }
  environment {
    REGISTRY       = 'myregistry.com'
    FRONTEND_IMAGE = 'myregistry.com/frontend'
    BACKEND_IMAGE  = 'myregistry.com/backend'
    TRIVY = 'docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache -v $PWD:/out aquasec/trivy:latest image --scanners vuln --severity HIGH,CRITICAL --timeout 15m'
  }
  stages {
    stage('Wait for docker') {
      steps {
        container('dind') {
          sh 'timeout 60 sh -c "until docker info >/dev/null 2>&1; do sleep 2; done"'
        }
      }
    }
    stage('Login registry') {
      steps {
        container('dind') {
          withCredentials([usernamePassword(credentialsId: 'registry-auth', usernameVariable: 'REG_USER', passwordVariable: 'REG_PW')]) {
            sh 'echo "$REG_PW" | docker login $REGISTRY -u "$REG_USER" --password-stdin'
          }
        }
      }
    }
    stage('Frontend build') {
      steps {
        container('dind') {
          sh 'docker build -f Dockerfile.frontend -t $FRONTEND_IMAGE:$BUILD_NUMBER -t $FRONTEND_IMAGE:latest .'
        }
      }
    }
    stage('Frontend trivy') {
      steps {
        container('dind') {
          sh 'eval $TRIVY --format template --template "@/contrib/html.tpl" -o /out/trivy-frontend.html $FRONTEND_IMAGE:$BUILD_NUMBER'
        }
      }
    }
    stage('Frontend push') {
      steps {
        container('dind') {
          sh 'docker push $FRONTEND_IMAGE:$BUILD_NUMBER && docker push $FRONTEND_IMAGE:latest'
        }
      }
    }
    stage('Backend build') {
      steps {
        container('dind') {
          sh 'docker build -f Dockerfile.backend -t $BACKEND_IMAGE:$BUILD_NUMBER -t $BACKEND_IMAGE:latest .'
        }
      }
    }
    stage('Backend trivy') {
      steps {
        container('dind') {
          sh 'eval $TRIVY --format template --template "@/contrib/html.tpl" -o /out/trivy-backend.html $BACKEND_IMAGE:$BUILD_NUMBER'
        }
      }
    }
    stage('Backend push') {
      steps {
        container('dind') {
          sh 'docker push $BACKEND_IMAGE:$BUILD_NUMBER && docker push $BACKEND_IMAGE:latest'
        }
      }
    }
  }
  post {
    always {
      archiveArtifacts artifacts: 'trivy-*.html', allowEmptyArchive: true
    }
  }
}
