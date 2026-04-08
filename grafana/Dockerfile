FROM grafana/grafana:10.4.0

# Bake provisioning (datasources + dashboard provider + dashboards) into the image.
# Grafana is stateless — all config lives in this repo.
# The Prometheus datasource URL is injected at runtime via PROMETHEUS_URL env var.
COPY grafana/provisioning /etc/grafana/provisioning
