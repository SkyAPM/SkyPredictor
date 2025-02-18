# Setting Override
SkyWalking Predictor supports setting overrides by system environment variables. 
You could override the settings in `config.yaml`

## System environment variables
- Example

  Override `server.grpc.port` in this setting segment through environment variables
  
```yaml
server:
  grpc:
    port: "${GRPC_PORT:18080}"
```

If the `GRPC_PORT ` environment variable exists in your operating system and its value is `9999`, 
then the value of `server.grpc.port` here will be overwritten to `9999`, otherwise, it will be set to `18080`.