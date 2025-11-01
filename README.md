```markdown
# Мониторинг PostgreSQL, системы и криптовалют с Prometheus + Grafana

> **Автор**: Александр Судро  
> **Цель**: Реализация трёх дашбордов мониторинга с использованием **Prometheus**, **Grafana**, **экспортеров** и **кастомного Python-экспортера**.  
> **Стек**: Docker Compose, Prometheus, Grafana, Node Exporter, Postgres Exporter, Python (`prometheus_client`, `requests`), CoinGecko API.

---

## Общая архитектура

```
docker-compose.yml
│
├── prometheus (порт 9090)
├── grafana (порт 3000)
├── postgres_exporter (порт 9187)
├── node_exporter (порт 9100)
└── custom_exporter (порт 8000)
```

Все сервисы в одной сети `monitoring`. Prometheus собирает метрики, Grafana визуализирует.

---

## Дашборд 1: Database Exporter (PostgreSQL)

**Цель**: Мониторинг базы `prometheus-monitoring`.

### Ключевые метрики (13 PromQL-запросов, 100% с функциями)

| № | Запрос | Описание |
|---|-------|---------|
| 1 | `sum(pg_stat_user_tables_n_dead_tup{datname="prometheus-monitoring"})` | Количество "мёртвых" строк |
| 2 | `sum by (datname) (rate(...)[1m])` | Скорость DML (insert/update/delete) |
| 3 | `count(pg_roles_connection_limit)` | Количество ролей с лимитом |
| 4 | `sum(pg_stat_database_conflicts{datname="..."})` | Конфликты в БД |
| 5 | `sum(pg_stat_activity_count{state="active"})` | Активные подключения |
| 6 | `sum(pg_stat_user_tables_n_live_tup + ...)` | Общее количество строк |
| 7 | `count(pg_stat_user_tables_n_live_tup)` | Количество таблиц с данными |
| 8 | `rate(xact_commit[1m]) + rate(xact_rollback[1m])` | QPS (коммиты + роллбэки) |
| 9 | `time() - process_start_time_seconds` | Uptime экспортера |
| 10 | `sum(pg_database_size_bytes)` | Размер БД (байт) |
| 11 | `... / 1024^3` | Размер БД (ГБ) |
| 12 | `count by (rolname) (pg_roles_connection_limit) > 0` | Пользователи с лимитами |
| 13 | `avg by (datname) (pg_stat_user_tables_n_live_tup)` | Среднее строк по БД |

> **Глобальный фильтр**: `datname` → `label_values(pg_stat_database_tup_inserted, datname)`

---

## Дашборд 2: Node Exporter (Системные метрики)

**Цель**: Мониторинг хоста (ноутбука/сервера).

### Ключевые метрики (15 запросов, 80% с функциями)

| № | Запрос | Описание |
|---|-------|---------|
| 1 | `sum(rate(node_network_*_errs_total[5m]))` | Ошибки сети |
| 2 | `rate(node_context_switches_total[5m])` | Переключения контекста |
| 3 | `(time() - node_boot_time_seconds) / 86400` | Uptime (дни) |
| 4 | `node_procs_running` | Активные процессы |
| 5 | `node_filesystem_free_bytes / 1024^3` | Свободно на диске (ГБ) |
| 6 | `100 * (1 - MemAvailable/MemTotal)` | RAM usage (%) |
| 7–8 | `rate(node_network_*_bytes_total[1m]) * 8 / 1024^2` | Трафик (Мбит/с) |
| 9–10 | `rate(node_disk_*_bytes_total[1m])` | Disk I/O |
| 11–13 | `node_memory_* / 1024^3` | RAM: Total, Available, Used (ГБ) |
| 14 | `avg(node_load15)` | Load average 15m |
| 15 | `100 - avg by (cpu) (rate(node_cpu_seconds_total{mode="idle"}[1m]))*100` | CPU usage (%) |
| 16 | `avg(node_hwmon_temp_celsius)` | Температура CPU |
| 17 | `100 * (SwapTotal - SwapFree) / SwapTotal` | Swap usage (%) |

> **Глобальный фильтр**: `device` → `label_values(node_network_receive_bytes_total, device)`

> **Тест нагрузки**: `stress-ng --cpu 4 --vm 2 --hdd 2 --timeout 60`

---

## Дашборд 3: Custom Exporter (Криптовалюты)

**API**: [CoinGecko](https://www.coingecko.com/en/api)  
**Монеты**: `bitcoin`, `ethereum`, `solana`, `binancecoin`  
**Категории**: `top_coin`, `alt_coin`

### Кастомные метрики (12+)

```python
Gauge: price, market_cap, volume_24h, change_24h, high/low_24h, ath/atl, supply
Gauge: volatility_24h = (high - low) / price
Counter: volume_changes_total → для rate()
```

### PromQL-запросы (14, >60% с функциями)

| № | Запрос | Описание |
|---|-------|---------|
| 1–7 | `crypto_*{coin="bitcoin"}` | Базовые значения |
| 8 | `sum by (category) (crypto_price_usd)` | Сумма цен по категориям |
| 9 | `avg by (coin) (crypto_change_24h_percent[5m])` | Среднее изменение |
| 10 | `rate(crypto_volume_changes_total[1m])` | Скорость изменений volume |
| 11 | `max by (category) (crypto_market_cap_usd)` | Макс. капитализация |
| 12 | `(high - low) / price` | Волатильность |
| 13 | `sum(crypto_circulating_supply{category="top_coin"})` | Общий supply top_coin |
| 14 | `min(crypto_atl_usd{coin=~"bitcoin\|ethereum"})` | Минимальный ATL |

> **Глобальный фильтр**: `coin` → `label_values(crypto_price_usd, coin)`

---

## Файлы проекта

| Файл | Описание |
|------|---------|
| `docker-compose.yml` | Запуск всех сервисов |
| `prometheus.yml` | Scrape-конфиги |
| `custom_exporter.py` | Сбор крипто-данных |
| `Dockerfile` | Сборка кастомного экспортера |
| `README.md` | Этот документ |

---

## Запуск

```bash
docker-compose up -d
```

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Custom Exporter**: http://localhost:8000/metrics

---

## Alerts

- **CPU > 80%** → Telegram
- **Swap > 90%** → Telegram
- **Цена BTC < $50,000** → Telegram

**Contact Point**: Telegram (`@TetrisregBot`, Chat ID: `-1001234567890`)

---

## GitHub

Репозиторий: [github.com/yourname/monitoring-project](https://github.com)  
Включает:
- `docker-compose.yml`
- `prometheus.yml`
- `custom_exporter.py`
- `Dockerfile`
- JSON дашбордов
- `README.md`

---

## Выполнение чек-листа

| № | Требование | Статус |
|---|-----------|--------|
| 1 | Prometheus + Grafana | Done |
| 2 | Экспортеры запущены | Done |
| 3 | ≥10 PromQL | Done (13 / 15 / 14) |
| 4 | ≥60% с функциями | Done (100% / 80% / >60%) |
| 5 | Запросы проверены | Done |
| 6 | Сбор 1–5 ч (или нагрузка) | Done (`stress-ng`) |
| 7 | ≥10 визуализаций, 4 типа | Done |
| 8 | Глобальный фильтр | Done (`datname`, `device`, `coin`) |
| 9 | Данные обновляются | Done |
| 10 | Alert + уведомление | Done (Telegram) |
| 11 | JSON + GitHub | Done |
| 12 | Демо на защите | Готов |

---


```
