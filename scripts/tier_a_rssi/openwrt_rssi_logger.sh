#!/bin/bash
#
# OpenWrt Router-side RSSI and Station Statistics Logger
#
# Collects per-station Wi-Fi statistics from an OpenWrt router (MT7628AN on Xiaomi Mi Router 4C).
# Logs signal strength, bitrate, connection time, and throughput metrics to a CSV file.
#
# This script runs ON THE ROUTER and monitors all connected stations.
#
# Hardware:
#   - Xiaomi Mi Router 4C with OpenWrt
#   - MT7628AN chipset
#   - Default interface: wlan0 (2.4 GHz)
#
# Usage on router (via SSH):
#   scp openwrt_rssi_logger.sh root@192.168.1.1:/tmp/
#   ssh root@192.168.1.1 "bash /tmp/openwrt_rssi_logger.sh \\
#       --output-file /tmp/router_stats.csv \\
#       --interval 1 \\
#       --interface wlan0"
#
# CSV Schema:
#   timestamp: ISO 8601 UTC
#   station_mac: Station MAC address (colon-separated)
#   signal_dbm: Signal strength in dBm (negative)
#   noise_dbm: Noise floor in dBm
#   rx_bitrate_mbps: RX bitrate in Mbps
#   tx_bitrate_mbps: TX bitrate in Mbps
#   rx_bytes: Total RX bytes since connection
#   tx_bytes: Total TX bytes since connection
#   rx_packets: Total RX packets since connection
#   tx_packets: Total TX packets since connection
#   connected_seconds: Connection duration in seconds
#   inactive_ms: Inactivity time in milliseconds
#   signal_avg_dbm: Average signal strength in dBm
#   authentication: Authentication status
#   authorization: Authorization status
#
# Requirements:
#   - iw command-line tool (iw package on OpenWrt)
#   - awk, date, bash (standard on OpenWrt)
#   - Connected Wi-Fi station(s)
#
# Notes:
#   - If no stations are connected, the script continues and logs nothing
#   - Timestamps use date command; ensure router time is accurate
#   - For dual-band collection, run this script for each interface (wlan0, wlan1)
#   - OpenWrt may need to have iw installed: opkg install iw
#

set -e

# Default values
OUTPUT_FILE="/tmp/router_stats.csv"
INTERVAL=1
INTERFACE="wlan0"
VERBOSE=0

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-file|-o)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --interval|-n)
            INTERVAL="$2"
            shift 2
            ;;
        --interface|-i)
            INTERFACE="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=1
            shift
            ;;
        --help|-h)
            cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --output-file FILE     Output CSV file path (default: /tmp/router_stats.csv)
  --interval SECONDS     Logging interval in seconds (default: 1)
  --interface IFACE      Wi-Fi interface to monitor (default: wlan0)
  --verbose              Enable verbose logging to stderr
  --help                 Show this help message

Example:
  bash $(basename "$0") \\
    --output-file /tmp/router_stats.csv \\
    --interval 1 \\
    --interface wlan0

EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Validate interval
if ! [[ "$INTERVAL" =~ ^[0-9]+(\.[0-9]+)?$ ]] || (( $(echo "$INTERVAL <= 0" | bc -l) )); then
    echo "ERROR: Interval must be a positive number" >&2
    exit 1
fi

# Logging function
log() {
    if (( VERBOSE )); then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
    fi
}

# Check if interface exists
if ! ip link show "$INTERFACE" > /dev/null 2>&1; then
    echo "ERROR: Interface '$INTERFACE' not found" >&2
    exit 1
fi

# Check if iw is available
if ! command -v iw &> /dev/null; then
    echo "ERROR: 'iw' command not found. Install with: opkg install iw" >&2
    exit 1
fi

# Create output directory if needed
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
if [[ ! -d "$OUTPUT_DIR" ]]; then
    mkdir -p "$OUTPUT_DIR" || {
        echo "ERROR: Cannot create output directory: $OUTPUT_DIR" >&2
        exit 1
    fi
fi

# Check if output file is new (for CSV header)
FILE_EXISTS=0
if [[ -f "$OUTPUT_FILE" ]]; then
    FILE_EXISTS=1
fi

log "Starting station statistics logger"
log "Interface: $INTERFACE"
log "Interval: ${INTERVAL}s"
log "Output: $OUTPUT_FILE"

# Write CSV header if file is new
if (( ! FILE_EXISTS )); then
    cat >> "$OUTPUT_FILE" <<EOF
timestamp,station_mac,signal_dbm,noise_dbm,rx_bitrate_mbps,tx_bitrate_mbps,rx_bytes,tx_bytes,rx_packets,tx_packets,connected_seconds,inactive_ms,signal_avg_dbm,authentication,authorization
EOF
    log "Created new CSV file with header"
fi

# Main logging loop
measurement_count=0

while true; do
    # Get station dump from iw
    station_dump=$(iw dev "$INTERFACE" station dump 2>/dev/null || true)

    if [[ -z "$station_dump" ]]; then
        # No stations connected
        log "No connected stations on $INTERFACE"
        sleep "$INTERVAL"
        continue
    fi

    # Parse station dump
    # iw station dump format (multiple stations separated by blank lines):
    # Station <MAC> (on <ifname>)
    #     connected time:    1234 ms
    #     inactive time:     123 ms
    #     rx bytes:          123456
    #     rx packets:        1234
    #     tx bytes:          654321
    #     tx packets:        5678
    #     tx retries:        12
    #     tx failed:         3
    #     signal:            -45 dBm
    #     signal avg:        -46 dBm
    #     tx bitrate:        72.2 Mbit/s MCS 7
    #     rx bitrate:        65.0 Mbit/s MCS 6
    #     authorized:        yes
    #     authenticated:     yes
    #     ...

    # Extract station MAC and properties
    current_mac=""
    declare -A station_data

    while IFS= read -r line; do
        # Match station MAC line
        if [[ $line =~ ^Station\ ([0-9a-fA-F:]+) ]]; then
            # If we have previous station data, save it
            if [[ -n "$current_mac" ]]; then
                # Write previous station to CSV
                write_station_record "$current_mac"
            fi
            current_mac="${BASH_REMATCH[1]}"
            # Reset data
            unset station_data
            declare -A station_data
            continue
        fi

        # Parse station properties (indented lines)
        if [[ $line =~ ^[[:space:]]+ ]]; then
            line=$(echo "$line" | xargs)  # Trim whitespace

            # Signal strength
            if [[ $line =~ ^signal:\ (-?[0-9]+)\ dBm ]]; then
                station_data[signal_dbm]="${BASH_REMATCH[1]}"
            fi

            # Signal average
            if [[ $line =~ ^signal\ avg:\ (-?[0-9]+)\ dBm ]]; then
                station_data[signal_avg_dbm]="${BASH_REMATCH[1]}"
            fi

            # RX bitrate
            if [[ $line =~ ^rx\ bitrate:\ ([0-9.]+)\ Mbit ]]; then
                station_data[rx_bitrate_mbps]="${BASH_REMATCH[1]}"
            fi

            # TX bitrate
            if [[ $line =~ ^tx\ bitrate:\ ([0-9.]+)\ Mbit ]]; then
                station_data[tx_bitrate_mbps]="${BASH_REMATCH[1]}"
            fi

            # RX bytes
            if [[ $line =~ ^rx\ bytes:\ ([0-9]+) ]]; then
                station_data[rx_bytes]="${BASH_REMATCH[1]}"
            fi

            # TX bytes
            if [[ $line =~ ^tx\ bytes:\ ([0-9]+) ]]; then
                station_data[tx_bytes]="${BASH_REMATCH[1]}"
            fi

            # RX packets
            if [[ $line =~ ^rx\ packets:\ ([0-9]+) ]]; then
                station_data[rx_packets]="${BASH_REMATCH[1]}"
            fi

            # TX packets
            if [[ $line =~ ^tx\ packets:\ ([0-9]+) ]]; then
                station_data[tx_packets]="${BASH_REMATCH[1]}"
            fi

            # Connected time (in ms, convert to seconds)
            if [[ $line =~ ^connected\ time:\ ([0-9]+)\ ms ]]; then
                station_data[connected_seconds]=$(echo "scale=2; ${BASH_REMATCH[1]} / 1000" | bc)
            fi

            # Inactive time
            if [[ $line =~ ^inactive\ time:\ ([0-9]+)\ ms ]]; then
                station_data[inactive_ms]="${BASH_REMATCH[1]}"
            fi

            # Authorization
            if [[ $line =~ ^authorized:\ ([a-z]+) ]]; then
                station_data[authorized]="${BASH_REMATCH[1]}"
            fi

            # Authentication
            if [[ $line =~ ^authenticated:\ ([a-z]+) ]]; then
                station_data[authenticated]="${BASH_REMATCH[1]}"
            fi
        fi
    done <<< "$station_dump"

    # Write last station
    if [[ -n "$current_mac" ]]; then
        write_station_record "$current_mac"
    fi

    measurement_count=$((measurement_count + 1))
    if (( measurement_count % 10 == 0 )); then
        log "Logged $measurement_count measurements"
    fi

    sleep "$INTERVAL"
done

# Function to write a station record to CSV
write_station_record() {
    local mac=$1
    local timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

    # Get values with defaults
    local signal_dbm=${station_data[signal_dbm]:-}
    local signal_avg_dbm=${station_data[signal_avg_dbm]:-}
    local rx_bitrate=${station_data[rx_bitrate_mbps]:-}
    local tx_bitrate=${station_data[tx_bitrate_mbps]:-}
    local rx_bytes=${station_data[rx_bytes]:-}
    local tx_bytes=${station_data[tx_bytes]:-}
    local rx_packets=${station_data[rx_packets]:-}
    local tx_packets=${station_data[tx_packets]:-}
    local connected_seconds=${station_data[connected_seconds]:-}
    local inactive_ms=${station_data[inactive_ms]:-}
    local auth=${station_data[authenticated]:-}
    local authz=${station_data[authorized]:-}

    # Noise floor (not directly available from iw, estimate from signal)
    # MT7628AN typical noise floor: -95 to -90 dBm
    local noise_dbm="-92"

    # Write CSV line
    echo "$timestamp,$mac,$signal_dbm,$noise_dbm,$rx_bitrate,$tx_bitrate,$rx_bytes,$tx_bytes,$rx_packets,$tx_packets,$connected_seconds,$inactive_ms,$signal_avg_dbm,$auth,$authz" >> "$OUTPUT_FILE"
}

# Trap for graceful exit
trap 'log "Logger stopped"; exit 0' SIGTERM SIGINT

log "Logger running. Press Ctrl+C to stop."
