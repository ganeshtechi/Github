#To check the current user
aws sts get-caller-identity

#updating kubeconfig with user
aws eks update-kubeconfig --name ganesh_syam

kebectl get pods -n kube-system
#To check my current namespace
current-ns

# To switch to different namespace
change-ns kube-system

#To switch to user1
source creds/user1
#To check the current user identity
aws sts get-caller-identity

#To get the pods in a specific namespace
kubectl get pods -n kube-system

#To create a simple deployment
kubectl create deployment nginx --image=nginx

