# Install AWS CLI
```
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

# Configure AWS CLI with access and secret keys

## verify aws cli version
aws --version 


# Install Eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin


# Install kubectl 
curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl 
sudo mv ./kubectl /usr/local/bin

#Verify kubectl version
kubectl version 

#Helm chart installation is required for prometheus and grafana setup
#Helm Chart works out of the box and it will take care of everything for you by installing prometheus-alertnamanger, prometheus-server, prometheus-operator

curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh


#Crate kubernetes cluster
eksctl create cluster --name dev-cluster-1 --version 1.22 --region us-east-1 --nodegroup-name dev_worker-nodes --node-type t2.large --nodes 2 --nodes-min 2 --nodes-max 3

#Install Metrics server
#Install the Kubernetes Metrics server onto the Kubernetes cluster so that Prometheus can collect the performance metrics of Kubernetes.

kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

#Verify metric servers installation
kubectl get deployment metrics-server -n kube-system or kubectl get pods -n kube-system

#Install promethus using helm 
#Add Prometheus helm chart repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 

#Update the helm chart repository
helm repo update 

#Verify repo list
helm repo list

# Create namespace prometheus
kubectl create namespace prometheus

#Install promethus
helm install prometheus prometheus-community/prometheus \
    --namespace prometheus \
    --set alertmanager.persistentVolume.storageClass="gp2" \
    --set server.persistentVolume.storageClass="gp2" 

#Verify prometheus objects
kubectl get all -n promethus

#View promethus Dashboard by forwarding the deployment ports
kubectl port-forward deployment/prometheus-server 9090:9090 -n prometheus

#Install Grafana
#Add the Grafana helm chart repository
helm repo add grafana https://grafana.github.io/helm-charts 

#Update the helm chart repository
helm repo update 


#Grafana needs input data soruce to visualize datasources:

"
prometheus-datasource.yaml
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-server.prometheus.svc.cluster.local
      access: proxy
      isDefault: true
"

#Create a seperate namespace for grafana
kubectl create namespace grafana

#Install Grafana

helm install grafana grafana/grafana \
    --namespace grafana \
    --set persistence.storageClassName="gp2" \
    --set persistence.enabled=true \
    --set adminPassword='EKS!sAWSome' \
    --values prometheus-datasource.yaml \
    --set service.type=LoadBalancer

#Verify grafana installation
kubectl get all -n grafana

#Get external IP to access grafana
kubectl get service -n grafana 

#We can create dashboards on our own or we can also import from opensource community
#https://grafana.com/grafana/dashboards/ is the repo 
#Use import option in Grafana to add the dashboard
#Deploy applications and monitor in Grafana dashboard.
