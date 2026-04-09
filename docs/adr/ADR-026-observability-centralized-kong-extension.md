# ADR-026: Observabilidade Centralizada — Expansão da Grafana Stack para Kong API Gateway

## Status

Aceito

## Data

2026-04-09

## Decision Makers

DevKitchen Team

## Tags

observability, monitoring, prometheus, loki, tempo, grafana, kong, apigateway, multi-service

---

## Contexto

A ADR-025 estabeleceu a stack de observabilidade (Prometheus + Loki + Tempo + Grafana) para o **Odoo**. Com a maturação da plataforma e a introdução do Kong API Gateway como camada de entrada, surgiu a necessidade de estender a cobertura de observabilidade para incluir o gateway.

Sem observabilidade no Kong, o time não consegue:

- Distinguir se um problema é no gateway ou no Odoo
- Medir latência total de ponta a ponta (Kong → Odoo → banco)
- Correlacionar um trace iniciado no Kong com o trace correspondente no Odoo

---

## Decisão

Expandir a Grafana Stack existente (ADR-025) para atuar como **hub de observabilidade multi-serviço**, adicionando cobertura completa do Kong API Gateway.

### Mudanças na stack do Odoo (`odoo-docker`)

**`docker-compose-production.yml`**

- `prometheus` adicionado à `dokploy-network` → pode fazer scrape do Kong via nome DNS `kong-gateway`
- `tempo` adicionado à `dokploy-network` → pode receber traces OTLP do Kong

**`observability/prometheus.yml`** — novo job:

```yaml
- job_name: "kong"
  static_configs:
    - targets: ["kong-gateway:8001"]
      labels:
        service: "kong-apigateway"
        tier: "gateway"
  metrics_path: "/metrics"
  scrape_interval: 15s
```

**`observability/promtail-config.yml`**

- Filtro por projeto Docker `180` removido → Promtail coleta logs de **todos** os containers do servidor
- Kong, token-refresher e futuros serviços são coletados automaticamente via Docker socket

**`observability/grafana/dashboards/kong-apigateway.json`** — dashboard novo, provisionado automaticamente, com 8 painéis:

1. Request rate por rota/serviço
2. Error rate (4xx/5xx) por status code
3. Latência p50/p95/p99
4. Upstream health status
5. Bandwidth ingress/egress
6. Distribuição de status codes
7. Logs do Kong (Loki)
8. Traces do Kong (Tempo)

### Dependência do `apigateway`

Detalhada na **ADR-004** do repositório `apigateway`:

- Plugin `prometheus` habilitado globalmente no Kong
- Plugin `opentelemetry` habilitado com endpoint `tempo:4318`

### Topologia de redes

```
dokploy-network (externa, compartilhada)
  ├── kong-gateway        (apigateway stack)
  ├── prometheus          (odoo stack — novo vínculo)
  ├── tempo               (odoo stack — novo vínculo)
  └── traefik             (dokploy)

odoo-net (interna, isolada)
  ├── odoo, db, redis, rabbitmq
  ├── prometheus, tempo, loki, grafana
  └── celery workers
```

---

## Consequências

### Positivas

- **Visibilidade end-to-end:** um único Grafana cobre Kong + Odoo + infra
- **Trace correlation:** W3C `traceparent` propagado pelo Kong chega ao Odoo e ambos os spans aparecem no mesmo trace no Tempo
- **Log correlation:** `X-Request-ID` gerado pelo Kong aparece nos logs do Odoo, permitindo busca cruzada no Loki
- **Zero novos containers:** nenhum recurso adicional de infra

### Negativas / Trade-offs

- `prometheus` e `tempo` passam a ter visibilidade na `dokploy-network`; risco mitigado pois são serviços sem portas expostas no host
- Coleta de logs de todos os containers aumenta levemente o volume no Loki; mitigável via `match`/`drop` no Promtail se necessário

---

## Relações

| Referência           | Tipo                                                 |
| -------------------- | ---------------------------------------------------- |
| ADR-025              | Estende (base da stack de observabilidade)           |
| ADR-004 (apigateway) | Complementar (configuração do lado Kong)             |
| ADR-008              | Contexto (segurança API — Admin API na rede interna) |
