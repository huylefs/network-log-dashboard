import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

ES_HOST = st.secrets["ES_HOST"]
ES_PORT = int(st.secrets.get("ES_PORT", 9243))
ES_USER = st.secrets["ES_USER"]
ES_PASS = st.secrets["ES_PASS"]
ES_SCHEME = st.secrets.get("ES_SCHEME","https")

SYSLOG_INDEX = "syslog-*"
METRIC_INDEX = "metricbeat-*"

es = Elasticsearch(
    hosts=[{"host": ES_HOST, "port": ES_PORT, "scheme": ES_SCHEME}], basic_auth=(ES_USER, ES_PASS), verify_certs=True)

# Convert time range to ES range
def get_time_range_gte(label: str) -> str:
    if label == "Last 15 minutes":
        return "now-15m"
    elif label == "Last 1 hour":
        return "now-1h"
    elif label == "Last 6 hours":
        return "now-6h"
    elif label == "Last 24 hours":
        return "now-24h"
    else:
        return "now-1h"

#Query syslog from Elasticsearch

def query_syslog(time_range_label: str, severity_codes=None, size: int = 500) -> pd.DataFrame:
    gte = get_time_range_gte(time_range_label)

    must_filters = [
	{"range": {"@timestamp": {"gte": gte, "lte": "now"}}}
    ]

    if severity_codes:
        must_filters.append({
	    "terms": {"log.syslog.severity.code": severity_codes}
	})

    body = {
	"size": size,
	"sort": [{"@timestamp": "desc"}],
	"_source": [
	    "@timestamp",
	    "message",
	    "host.hostname",
	    "host.ip",
	    "log.syslog.severity.code",
	    "log.syslog.severity.name",
	],
	"query": {
	    "bool": {
		"filter": must_filters
	    }
	}
    }

    res = es.search(index=SYSLOG_INDEX, body=body)
    hits = res.get("hits", {}).get("hits", [])

    rows = []
    for h in hits:
        src = h.get("_source", {})
        host = src.get("host", {}) or {}
        log_sys = src.get("log", {}).get("syslog", {}) or {}
        sev = log_sys.get("severity", {}) or {}

        rows.append({
	    "timestamp": src.get("@timestamp"),
	    "hostname": host.get("hostname"),
	    "host_ip": host.get("ip"),
	    "severity_code": sev.get("code"),
	    "severity_name": sev.get("name"),
	    "message": src.get("message"),
	})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

#Query metricbeat

def query_metrics(time_range_label: str, size: int = 1000) -> pd.DataFrame:
    gte = get_time_range_gte(time_range_label)

    body = {
	"size": size,
	"sort": [{"@timestamp": "desc"}],
	"_source": [
	    "@timestamp",
	    "host.hostname",
	    "host.ip",
	    "system.cpu.total.norm.pct",
	    "system.memory.actual.used.pct",
	    "system.filesystem.used.pct",
	    "system.filesystem.mount_point",
	],
	"query": {
	    "bool": {
		"filter": [
		    {"range": {"@timestamp": {"gte": gte, "lte": "now"}}}
		]
	    }
	}
    }

    res = es.search(index=METRIC_INDEX, body=body)
    hits = res.get("hits", {}).get("hits", [])

    rows = []
    for h in hits:
        src = h.get("_source", {})
        host = src.get("host", {}) or {}
        fs = src.get("system", {}).get("filesystem", {}) or {}
        rows.append({
	    "timestamp": src.get("@timestamp"),
	    "hostname": host.get("hostname"),
	    "host_ip": host.get("ip"),
	    "cpu_pct": src.get("system", {}).get("cpu", {}).get("total", {}).get("norm", {}).get("pct"),
	    "mem_used_pct": src.get("system", {}).get("memory", {}).get("actual", {}).get("used", {}).get("pct"),
	    "fs_used_pct": fs.get("used", {}).get("pct"),
	    "fs_mount": fs.get("mount_point"),
	})

    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

#Streamlit layout
st.set_page_config(
    page_title= "Network Log Dashboard",
    layout="wide"
)

st.title("Network Monitoring Dashboard")
st.caption("Built with Streamlit +Elasticsearch")

st.sidebar.header("Controls")

dashboard_type = st.sidebar.radio(
    "Select dashboard",
    ["Syslog Logs", "Metrics (CPU/RAM/Disk)", "Network Devices (VyOS)"],
    index=0
)

time_range = st.sidebar.selectbox(
    "Time range",
    ["Last 15 minutes", "Last 1 hour", "Last 6 hours", "Last 24 hours"],
    index=1
)

st.sidebar.markdown("---")

#Syslog dashboard
if dashboard_type == "Syslog Logs":
    st.subheader("Syslog Events")

    sev_options = {
        "All severities": None,
        "Only critical (0-3)": [0, 1, 2, 3],
        "Warning and above (0-4)": [0, 1, 2, 3, 4],
        "Notice and above (0-5)": [0, 1, 2, 3, 4, 5],
    }

    sev_label = st.sidebar.selectbox(
        "Severity filter",
        list(sev_options.keys()),
        index=0
    )
    sev_codes = sev_options[sev_label]

    message_query = st.sidebar.text_input(
        "Search in message (optional)",
        value=""
    )

    st.sidebar.markdown("---")
    refresh = st.sidebar.button("Refresh data")

    df = query_syslog(time_range, sev_codes)
    if df.empty:
        st.warning("No syslog events found for the selected range.")
    else:
        df = df[df["message"].str.contains(message_query, case=False, na=False)]

    if df.empty:
        st.info("No events match the message filter.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total events", len(df))
        with col2:
            error_count = (df["severity_code"] <= 3).sum()
            st.metric("Error events (severity <= 3)", int(error_count))
        with col3:
            host_count = df["hostname"].nunique()
            st.metric("Hosts with events", int (host_count))

        st.markdown("### Event over time")
        df_chart = df.copy()
        df_chart["time_bucket"] = df_chart["timestamp"].dt.floor("1min")

        chart_data = (
            df_chart
            .groupby(["time_bucket", "severity_name"])
            .size()
            .reset_index(name="count")
	)

        pivot = chart_data.pivot(
            index="time_bucket",
            columns="severity_name",
            values="count"
        ).fillna(0)

        st.line_chart(pivot)
        st.markdown("### Detailed syslog events")

        host_filter = st.multiselect(
            "Filter by hostname",
            options=sorted(df["hostname"].dropna().unique()),
            default=None
	)

        df_show = df.copy()
        if host_filter:
            df_show = df_show[df_show["hostname"].isin(host_filter)]

        df_show = df_show.sort_values("timestamp", ascending=False)
        df_show = df_show[
            ["timestamp", "hostname", "host_ip",
            "severity_code", "severity_name", "message"]
        ]

        st.dataframe(
            df_show,
            use_container_width=True,
            height=500
	)

#Metrics dashboard
elif dashboard_type == "Metrics (CPU/RAM/Disk)":
    st.subheader("Host Metrics (CPU /Memory / Disk)")

    dfm = query_metrics(time_range)
    if dfm.empty:
        st.warning("No metricbeat data found for the selected range.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            hosts = dfm["hostname"].nunique()
            st.metric("Number of hosts", int(hosts))
        with col2:
            avg_cpu = dfm["cpu_pct"].mean() * 100 if dfm["cpu_pct"].notna().any() else None
            st.metric("Average CPU usage (%)", f"{avg_cpu:.1f}"if avg_cpu is not None else "N/A")
        with col3:
            avg_mem = dfm["mem_used_pct"].mean() * 100 if dfm["mem_used_pct"].notna().any() else None
            st.metric("Average Memory usage(%)", f"{avg_mem:.1f}" if avg_mem is not None else "N/A")
        host_filter = st.multiselect(
            "Filter by hostname",
            options=sorted(dfm["hostname"].dropna().unique()),
            default=None
        )

        dfm_show = dfm.copy()
        if host_filter:
            dfm_show = dfm_show[dfm_show["hostname"].isin(host_filter)]

        if dfm_show.empty:
            st.info("No metric match the selected host filter.")
        else:
            st.markdown("### CPU Usage over time")
            cpu_df = dfm_show[dfm_show["cpu_pct"].notna()].copy()
            if not cpu_df.empty:
                cpu_df["time_bucket"] = cpu_df["timestamp"].dt.floor("1min")
                cpu_chart = (
                    cpu_df
                    .groupby(["time_bucket", "hostname"])["cpu_pct"]
                    .mean()
                    .reset_index()
                )
                pivot_cpu = cpu_chart.pivot(
                    index="time_bucket",
                    columns="hostname",
                    values="cpu_pct"
                )
                st.line_chart(pivot_cpu)
            else:
                st.info("No CPU data available.")
            st.markdown("### Memory usage over time")
            mem_df = dfm_show[dfm_show["mem_used_pct"].notna()].copy()
            if not mem_df.empty:
                mem_df["time_bucket"] = mem_df["timestamp"].dt.floor("1min")
                mem_chart = (
                    mem_df
                    .groupby(["time_bucket", "hostname"])["mem_used_pct"]
                    .mean()
                    .reset_index()
                )
                pivot_mem = mem_chart.pivot(
                    index="time_bucket",
                    columns="hostname",
                    values="mem_used_pct"
                )
                st.line_chart(pivot_mem)
            else:
                st.info("No memory data available.")
            st.markdown("### Disk usage(latest snapshot)")

            disk_df = dfm_show[dfm_show["fs_used_pct"].notna()].copy()
            if not disk_df.empty:
                disk_df = disk_df.sort_values("timestamp").groupby(
                    ["hostname", "fs_mount"], as_index=False
                ).tail(1)

                disk_df["fs_used_pct"] = disk_df["fs_used_pct"] * 100
                disk_df = disk_df[
                    ["hostname", "host_ip", "fs_mount", "fs_used_pct"]
                ].sort_values("fs_used_pct", ascending=False)

                st.dataframe(
                    disk_df,
                    use_container_width=True,
                    height=300
                )
            else:
                st.info("No filesystem usage data available.")

#VyOS dashboard
elif dashboard_type == "Network Devices (VyOS)":
    st.subheader("Network Device Logs (VyOS)")

    keyword = st.sidebar.text_input(
        "Hostname contains (for VyOS)",
        value="vyos"
    )

    sev_label_vyos = st.sidebar.selectbox(
        "Severity filter",
        ["All severities", "Only errors (<= 3)", "Only warnings and above (<= 4"],
        index=0
    )
    if sev_label_vyos == "All severities":
        sev_codes_vyos = None
    elif sev_label_vyos == "Only errors (<= 3)":
        sev_codes_vyos = [0, 1, 2, 3]
    else:
        sev_codes_vyos = [0, 1, 2, 3, 4]

    df_vyos = query_syslog(time_range, sev_codes_vyos)

    if df_vyos.empty:
        st.warning("No syslog events found for the selected range.")
    else:
        df_vyos = df_vyos[
            df_vyos["hostname"].str.contains(keyword, case=False, na=False)
        ]

        if df_vyos.empty:
            st.info(f"No events found for hostnames containing '{keyword}'.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total VyOS events", len(df_vyos))
            with col2:
                unique_hosts = df_vyos["hostname"].nunique()
                st.metric("Number of VyOS hosts", int(unique_hosts))

            st.markdown("### Severity distribution")
            sev_dist = (
                df_vyos
                .groupby("severity_name")
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
            )
            st.bar_chart(
                data=sev_dist.set_index("severity_name")["count"]
            )

            st.markdown("### VyOS events over time")
            vyos_chart = df_vyos.copy()
            vyos_chart["time_bucket"] = vyos_chart["timestamp"].dt.floor("1min")

            vyos_chart_data = (
                vyos_chart
                .groupby(["time_bucket", "severity_name"])
                .size()
                .reset_index(name="count")
            )

            vyos_pivot = vyos_chart_data.pivot(
                index= "time_bucket",
                columns="severity_name",
                values="count"
            ).fillna(0)

            st.line_chart(vyos_pivot)

            st.markdown("### VyOs syslog events")
            df_vyos_show = df_vyos.sort_values("timestamp", ascending=False)
            df_vyos_show = df_vyos_show[
                ["timestamp", "hostname", "host_ip",
                "severity_code", "severity_name", "message"]
            ]

            st.dataframe(
                df_vyos_show,
                use_container_width=True,
                height=500
            )
