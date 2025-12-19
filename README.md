# Network Log Dashboard

A real-time network monitoring dashboard built with **Streamlit** and **Elasticsearch**, providing comprehensive visibility into system metrics, security events, syslog data, and network device logs.

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Dashboard Modules](#-dashboard-modules)
- [Data Sources](#-data-sources)
- [Troubleshooting](#-troubleshooting)

## ✨ Features

### Multi-Language Support
- **English** and **Vietnamese (Tiếng Việt)**
- Seamless language switching via sidebar

### Four Comprehensive Dashboard Modules

| Module | Description |
|--------|-------------|
| **System Metrics** | CPU, Memory, and Disk usage monitoring with trend analysis |
| **Security (SSH)** | Failed login attempts tracking and security event analysis |
| **Syslog** | Centralized syslog event viewer with severity filtering |
| **Network Devices (VyOS)** | Dedicated monitoring for VyOS network equipment |

### Key Capabilities
- ⏱️ **Flexible Time Ranges**: 15 minutes, 1 hour, 6 hours, or 24 hours
- 🔍 **Advanced Filtering**: Filter by hostname, severity level, and message content
- 📊 **Interactive Visualizations**: Line charts, pie charts, and styled data tables
- 🔄 **Real-time Refresh**: Manual data refresh with cache clearing
- 🎨 **Color-coded Alerts**: Visual highlighting for critical metrics (>75% threshold)

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Data Sources  │───> │  Elasticsearch  │───> │    Streamlit    │
│                 │     │    Cluster      │     │    Dashboard    │
│ • Syslog        │     │                 │     │                 │
│ • Metricbeat    │     │ • syslog-*      │     │ • System Status │
│                 │     │ • metricbeat-*  │     │ • Security      │
│                 │     │                 │     │ • Syslog Viewer │
│                 │     │                 │     │ • VyOS Logs     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 📦 Prerequisites

- **Python**: 3.8 or higher
- **Elasticsearch**: 8.x cluster with:
  - `syslog-*` index (for syslog data)
  - `metricbeat-*` index (for system metrics)
- **Network Access**: Connectivity to Elasticsearch cluster

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/network-log-dashboard.git
cd network-log-dashboard
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `streamlit` - Web application framework
- `pandas` - Data manipulation and analysis
- `elasticsearch>=8.0.0,<9.0.0` - Elasticsearch Python client
- `plotly>=6.0.0` - Interactive visualizations

## ⚙️ Configuration

### Streamlit Secrets

Create a `.streamlit/secrets.toml` file in your project directory:

```toml
# Elasticsearch Configuration
ES_HOST = "your-elasticsearch-host.com"
ES_PORT = 9243
ES_USER = "your-username"
ES_PASS = "your-password"
ES_SCHEME = "https"
```

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ES_HOST` | Elasticsearch hostname or IP | *Required* |
| `ES_PORT` | Elasticsearch port | `9243` |
| `ES_USER` | Authentication username | *Required* |
| `ES_PASS` | Authentication password | *Required* |
| `ES_SCHEME` | Connection scheme (`http`/`https`) | `https` |

### Elasticsearch Index Patterns

The dashboard queries the following index patterns:

- **`syslog-*`**: Contains syslog events with fields:
  - `@timestamp`, `message`, `host.hostname`, `host.ip`
  - `log.syslog.severity.code`, `log.syslog.severity.name`

- **`metricbeat-*`**: Contains system metrics with fields:
  - `@timestamp`, `host.hostname`, `host.ip`
  - `system.cpu.total.norm.pct`
  - `system.memory.actual.used.pct`
  - `system.filesystem.used.pct`, `system.filesystem.mount_point`

## 📖 Usage

### Running the Dashboard

```bash
streamlit run app.py
```

The dashboard will be available at `http://localhost:8501`

### Running with Custom Port

```bash
streamlit run app.py --server.port 8080
```

### Running in Production

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 80
```

## 📊 Dashboard Modules

### 1. System Metrics

Monitor the health of your infrastructure:

- **Status Board Table**
  - Hostname, IP Address, Last Seen timestamp
  - Average CPU %, Memory %, and Root Disk %
  - Color-coded cells (red) when metrics exceed 75%

- **Trend Charts**
  - CPU usage over time (per host)
  - Memory usage over time (per host)
  - Multi-select host filtering

### 2. Security Dashboard

Track SSH security events:

- **Metrics**
  - Total failed login attempts count

- **Visualizations**
  - Recent failed login events table
  - Bar chart of top hosts with failures

- **Detection Pattern**
  - Searches for "Failed password" in syslog messages

### 3. Syslog Dashboard

Centralized log management:

- **Filters**
  - Hostname multi-select
  - Severity filter (All, Critical 0-3, Warning 0-4, Notice 0-5)
  - Message text search

- **Visualizations**
  - Total events and error events metrics
  - Events over time (line chart by severity)
  - Severity distribution (pie chart)
  - Detailed events table

### 4. VyOS Network Device Dashboard

Dedicated view for network equipment:

- **Filters**
  - Hostname keyword filter (default: "vyos")
  - Severity filter
  - Message search

- **Metrics & Charts**
  - Total VyOS events count
  - Number of unique VyOS hosts
  - Events timeline by severity
  - Severity distribution pie chart
  - Detailed log table

## 📡 Data Sources

### Syslog Severity Levels

| Code | Name | Description |
|------|------|-------------|
| 0 | Emergency | System is unusable |
| 1 | Alert | Action must be taken immediately |
| 2 | Critical | Critical conditions |
| 3 | Error | Error conditions |
| 4 | Warning | Warning conditions |
| 5 | Notice | Normal but significant condition |
| 6 | Informational | Informational messages |
| 7 | Debug | Debug-level messages |

### Expected Data Format

**Syslog Document Example:**
```json
{
  "@timestamp": "2024-01-15T10:30:00.000Z",
  "message": "Failed password for root from 192.168.1.100 port 22 ssh2",
  "host": {
    "hostname": "server-01",
    "ip": "10.0.0.1"
  },
  "log": {
    "syslog": {
      "severity": {
        "code": 4,
        "name": "warning"
      }
    }
  }
}
```

**Metricbeat Document Example:**
```json
{
  "@timestamp": "2024-01-15T10:30:00.000Z",
  "host": {
    "hostname": "server-01",
    "ip": "10.0.0.1"
  },
  "system": {
    "cpu": {
      "total": {
        "norm": {
          "pct": 0.45
        }
      }
    },
    "memory": {
      "actual": {
        "used": {
          "pct": 0.72
        }
      }
    },
    "filesystem": {
      "used": {
        "pct": 0.55
      },
      "mount_point": "/"
    }
  }
}
```

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Connection refused | Verify ES_HOST and ES_PORT in secrets.toml |
| Authentication failed | Check ES_USER and ES_PASS credentials |
| No data displayed | Ensure index patterns exist and contain data |
| SSL certificate errors | The app disables SSL verification by default |

### Debugging

Enable Elasticsearch query debugging by checking the Streamlit error messages displayed when queries fail.



