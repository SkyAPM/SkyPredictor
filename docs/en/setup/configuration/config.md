# configuration

## Logging

Configure system logs in SkyWalking Predictor.

| Name           | Default                                               | Environment Key | Description               |
|----------------|-------------------------------------------------------|-----------------|---------------------------|
| logging.level  | INFO                                                  | LOGGING_LEVEL   | Minimum log output level. |
| logging.format | :%(asctime)s - %(name)s - %(levelname)s - %(message)s | LOGGING_FORMAT  | Log output format.        |

## server

Configure the external services provided by SkyWalking Predictor.

| Name                   | Default | Environment Key | Description                                              |
|------------------------|---------|-----------------|----------------------------------------------------------|
| server.grpc.port       | 18080   | GRPC_PORT       | Port for providing external gRPC services.               |
| server.monitor.enabled | true    | MONITOR_ENABLED | Whether to enable Prometheus metrics monitoring service. |
| server.monitor.port    | 8000    | MONITOR_PORT    | Port for providing external monitoring services.         |

## baseline

Configure how to fetch data, and prediction metrics for dynamic baseline.

Please make these module in OAP have been activated:
1. **status-query**: Query `/status/config/ttl` for getting TTL of days for fetch all metrics data.
2. **graph** in **query**: Query service, metrics from GraphQL.

| Name                                | Default                 | Environment Key                     | Description                                                                                                                                             |
|-------------------------------------|-------------------------|-------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| baseline.cron                       | */8 * * * *             | BASELINE_FETCH_CRON                 | Configure the execution timing of data retrieval and prediction for the baseline by a cron expression.                                                  |
| baseline.fetch.server.address       | http://localhost:12800/ | BASELINE_FETCH_SERVER_ENDPOINT      | Address of OAP Restful server.                                                                                                                          |
| baseline.fetch.server.username      |                         | BASELINE_FETCH_SERVER_USERNAME      | If OAP access requires authentication, the username must be provided.                                                                                   |
| baseline.fetch.server.password      |                         | BASELINE_FETCH_SERVER_USERNAME      | If OAP access requires authentication, the password must be provided.                                                                                   |
| baseline.fetch.server.down_sampling | HOUR                    | BASELINE_FETCH_SERVER_DOWN_SAMPLING | Specify the type of downsampling data to download from OAP, supporting `HOUR` and `MINUTE`. Note that retrieving minute-level data takes a longer time. |
| baseline.fetch.server.layers        | GENERAL                 | BASELINE_FETCH_SERVER_LAYERS        | Specify which layer service data needs to be fetch. Use a comma(`,`) to separate multiple layers.                                                       |
| baseline.fetch.metrics              |                         |                                     | List of metrics to be monitored.                                                                                                                        |
| baseline.fetch.metrics.name         |                         |                                     | Metric name.                                                                                                                                            |
| baseline.fetch.metrics.enabled      |                         |                                     | Is active the Metric or not.                                                                                                                            |
| baseline.fetch.predict.directory    | ./out_predict           | BASELINE_PREDICT_DIRECTORY          | The directory for save prediction results for query purposes.                                                                                           |
| baseline.fetch.predict.min_days     | 2                       | BASELINE_PREDICT_MIN_DAYS           | The minimum number of days of data required for metric prediction, preventing inaccuracies due to insufficient data.                                    |
| baseline.fetch.predict.frequency    | h                       | BASELINE_PREDICT_FREQUENCY          | Specify the frequency of the predicted data. Currently, only hourly (`h`) is supported.                                                                 |
| baseline.fetch.predict.period       | 24                      | BASELINE_PREDICT_PERIOD             | Specify the number of future data points to predict.                                                                                                    |

