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
        memory: "512Mi"
      limits:
        memory: "1536Mi"
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
    REGISTRY = 'myregistry.com'
    IMAGE    = 'myregistry.com/frontend'
  }
  stages {
    stage('Wait for docker') {
      steps {
        container('dind') {
          sh 'timeout 60 sh -c "until docker info >/dev/null 2>&1; do sleep 2; done"'
        }
      }
    }
    stage('Build frontend') {
      steps {
        container('dind') {
          sh 'docker build -f Dockerfile.frontend -t $IMAGE:$BUILD_NUMBER -t $IMAGE:latest .'
        }
      }
    }
    stage('Push frontend') {
      steps {
        container('dind') {
          withCredentials([usernamePassword(credentialsId: 'registry-auth', usernameVariable: 'REG_USER', passwordVariable: 'REG_PW')]) {
            sh '''
              echo "$REG_PW" | docker login $REGISTRY -u "$REG_USER" --password-stdin
              docker push $IMAGE:$BUILD_NUMBER
              docker push $IMAGE:latest
            '''
          }
        }
      }
    }
  }
}
