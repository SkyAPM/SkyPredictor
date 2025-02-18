# Deploy on Kubernetes

This documentation helps you to set up the SkyWalking Predictor in the Kubernetes environment.

## Startup Kubernetes

Make sure that you already have a Kubernetes cluster.

If you don't have a running cluster, you can also leverage [KinD (Kubernetes in Docker)](https://kind.sigs.k8s.io)
or [minikube](https://minikube.sigs.k8s.io) to create a cluster.

## Configure Metrics

Please edit the [config.yaml](./configmap.yaml) file to deploy in your Kubernetes cluster. 
The following configuration need to be updated:
1. **OAP Restful Address**: The Restful Address of OAP to fetch metrics data.
2. **Metrics List**: Which metrics need to be fetched for prediction.

For details, refer to the [configuration documentation](../../configuration/config.md).

## Deploy Predictor

Please follow the [deployment.yml](deployment.yml) to deploy the predictor in your Kubernetes cluster.
Update the comment in the file, which includes two configs:
1. **PVC Storage Size**: The storage size for storage the prediction result.

Then, you could use `kubectl apply -f deployment.yml` to deploy the SkyWalking Predictor into your cluster.

NOTE: The Predictor service currently does not support cluster awareness. 
Additionally, due to the `ReadWriteOnce` limitation of PVC, it can only be deployed on a single node.