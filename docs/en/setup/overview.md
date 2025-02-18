# Setup

The first and most important thing is, that SkyWalking Predictor startup behaviors are driven by [config.yaml](../../../config/config.yaml). 
Understanding the setting file will help you to read this document.

### SkyWalking OAP Compatibility

The SkyWalking Predictor requires specialized protocols to communicate with SkyWalking OAP.

| SkyWalking Predictor Version | SkyWalking OAP | Notice |
|------------------------------|----------------|--------|
| 0.1.0+                       | \> = 10.2.0    |        | 


## Configuration

Please refer to [this document](configuration/config.md) for the configuration file details.

To adjust the configurations, refer to [Overriding Setting](./configuration/override-settings.md) document for more details.

## Deployments

Currently, the following two deployment methods are supported:

1. [**Single VM Node**](deployment/vm/readme.md): Deploy on a single node in a VM.
2. [**Kubernetes**](deployment/kubernetes/readme.md): Deploy as a single node within a Kubernetes cluster.