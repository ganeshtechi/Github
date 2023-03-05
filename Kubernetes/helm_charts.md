# Install AWS CLI


Helm is package manager for kubernetes like yum and apt in linux boxes.  
Manage installation of Kubernetes applications.  
Helm uses a packaging format called charts.  
If we have manifest files for multiple applications, services, deployments, config maps, secrets we can package all of them into chart.
Definition: A chart is a collections of files that described a related set of K8 services.
When we run that chart it install all of them. 
We can update the charts, rollout new version.
We can also dry run to verify objects before we install.
kubectl must be configured to connect with the cluster other wise it throws an error.  
Make sure kubectl configured with the cluster and intended namespace.  
We can also download publicly available helm charts from the repo https://artifacthub.io/.  
We can also customize the default provided values but there will be limiatation that will be provided in the charts documents.  
When we install the helm chart it start with Revision1 and when we update anything it makes the Revision2.  
Always roll back to any version.  


# Helm charts structure

charts.yml:
	Meta information about the chart
values.yml: 
	Contains the values for the template file. It's like variable, we call these values in templates. 
Charts: 
	Contains other dependent charts. 
Teamplates: 
	Where you put all the manifest files that you are deploying with charts, Ex: 


# Install helm
Download the binary from https://github.com/helm/helm/releases
extract and move the helm binary to system bin location 
```
mv helm /usr/local/bin/helm
```

If we try to pull any chart from public repo, we must have to add the repo to our local helm. 
```
helm repo add bitnami https://charts.bitnami.com/bitnami
```

list all added repositories
```
helm repo ls
```

We can search for charts either in the artifact hub or locally configured repo. 
```
helm search repo nginx
```

```
helm search hub nginx
```


# To intall the charts

```
helm install my_webserver bitnami/nginx
```

It will install all respective objects, pods, replicaset, deployment, service etc.

To list all installed helm charts in the current namespace

```
helm ls
```

To list all installed helm charts in other namespace
```
helm ls --namespace default 
```

We can overwrite default values.  
```
helm install wordpress bitnami/wordpress --values=wordpress-values.yml
```

wordpress-values.yml file has custom values.  

We can upgrade our helm chart at any point of time.  
```
helm upgrade wordpress bitnami/wordpress --values=wordpress-values.yml 
```
We can check history of helm charts.  
```
helm history project_name
```

To roll back the helm chart revision
```
helm rollback project_name Revision_number
```

Even the rollback create a new revision.  
