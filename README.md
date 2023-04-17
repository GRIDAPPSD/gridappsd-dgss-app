# Ditributed Grid Sensing Services Application

## Installation Steps:

### Pre-requisite
- Kubernetes (via Minikube or Docker Desktop)
- kubectl
- Python3

### Create Kubernetes and Kafka cluster environment
In a terminal
1. `git clone https://github.com/GRIDAPPSD/gridappsd-dgss-app.git`
2. `cd gridappsd-dgss-app`
3. `kubectl create namespace kafka`
4. `kubectl create -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka`
5. `kubectl apply -f dgss-kafka.yaml -n kafka`
6. `kubectl wait kafka/my-cluster --for=condition=Ready --timeout=300s -n kafka`

### To run Python application on host machine's local environment

1. `pip install -r requirements.txt`
2. `cd src`
3. `python kafka_consumer.py`
4. In another terminal: `python kafka_producer.py`

### To run Python application in Kubernetes

1. `docker build -f Dockerfile -t dgss-app:latest .`
2. `kubectl apply -f dgss-app.yaml -n kafka`
3. `kubectl exec -it dgss-app-0 -- /bin/bash`
4. `python kafka_consumer.py`
5. In another terminal: `python kafka_producer.py`
