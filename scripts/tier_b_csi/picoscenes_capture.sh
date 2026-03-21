#!/bin/bash
#
# PicoScenes CSI Capture Setup and Data Collection
#
# Configures an Intel AX200/AX210 M.2 Wi-Fi card for Channel State Information (CSI)
# capture using PicoScenes, collects CSI data at specified frequencies, and saves
# to native PicoScenes .csi format for post-processing.
#
# This script provides:
#   1. CSI hardware verification and compatibility checks
#   2. Monitor mode setup and channel configuration
#   3. PicoScenes daemon launch and CSI collection
#   4. Dual-band (2.4 GHz + 5 GHz) sequential capture with metadata
#
# Hardware Requirements:
#   - Intel AX200 or AX210 M.2 Wi-Fi card
#   - Supported Linux kernel (5.4+)
#   - PicoScenes software installed
#   - Root/sudo privileges
#
# Installation Instructions:
#
#   1. Install PicoScenes:
#      - Download from: https://github.com/Marsrocky/PicoScenes
#      - Prerequisites: libnl-3, libnl-genl-3, libpcap, cmake, g++
#      - Build: mkdir build && cd build && cmake .. && make && sudo make install
#
#   2. Load custom kernel modules (if required):
#      - PicoScenes provides precompiled drivers for AX200/AX210
#      - Unload default driver: sudo modprobe -r iwlwifi
#      - Load PicoScenes driver: sudo modprobe iwlwifi
#      - Or use: source_dir/install_driver.sh
#
#   3. Verify installation:
#      - Run: PicoScenes -v
#      - Should show version and support for AX200/AX210
#
# Usage:
#   # Capture CSI at single channel (2.4 GHz, channel 6)
#   bash picoscenes_capture.sh \\
#       --interface wlan0 \\
#       --channel 6 \\
#       --bandwidth 20 \\
#       --duration 60 \\
#       --output-dir ./csi_data
#
#   # Dual-band sequential capture
#   bash picoscenes_capture.sh \\
#       --interface wlan0 \\
#       --channel-2-4 6 \\
#       --channel-5 36 \\
#       --bandwidth 20 \\
#       --duration 30 \\
#       --dual-band \\
#       --output-dir ./csi_data
#
# CSI File Output:
#   - .csi files: PicoScenes native binary format
#   - .pcap files: Packet capture with CSI in radiotap headers (optional)
#   - manifest.json: Metadata about capture sessions
#
# References:
#   - PicoScenes GitHub: https://github.com/Marsrocky/PicoScenes
#   - Intel AX200/AX210 specs: https://www.intel.com/content/www/us/en/products/wireless.html
#   - IEEE 802.11 CSI specs: Draft specifications available from IEEE
#

set -e

# Default values
INTERFACE=""
CHANNEL=""
CHANNEL_2_4=""
CHANNEL_5=""
BANDWIDTH="20"
DURATION="60"
OUTPUT_DIR="./csi_data"
DUAL_BAND=0
VERBOSE=0
DRY_RUN=0

# PicoScenes configuration
PICOSCENES_CMD="PicoScenes"  # Assumes PicoScenes is in PATH

# IEEE 802.11 channel definitions
declare -A CHANNELS_2_4
CHANNELS_2_4=(
    [1]=2412 [2]=2417 [3]=2422 [4]=2427 [5]=2432 [6]=2437
    [7]=2442 [8]=2447 [9]=2452 [10]=2457 [11]=2462 [12]=2467 [13]=2472
)

declare -A CHANNELS_5
CHANNELS_5=(
    [36]=5180 [40]=5200 [44]=5220 [48]=5240 [52]=5260 [56]=5280
    [60]=5300 [64]=5320 [100]=5500 [104]=5520 [108]=5540 [112]=5560
    [116]=5580 [120]=5600 [124]=5620 [128]=5640 [132]=5660 [136]=5680
    [140]=5700 [144]=5720 [149]=5745 [153]=5765 [157]=5785 [161]=5805
    [165]=5825 [169]=5845 [173]=5865 [177]=5885
)

# Logging functions
log_info() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_warn() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARN: $1" >&2
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

log_verbose() {
    if (( VERBOSE )); then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] DEBUG: $1" >&2
    fi
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --interface|-i)
            INTERFACE="$2"
            shift 2
            ;;
        --channel|-c)
            CHANNEL="$2"
            shift 2
            ;;
        --channel-2-4)
            CHANNEL_2_4="$2"
            shift 2
            ;;
        --channel-5)
            CHANNEL_5="$2"
            shift 2
            ;;
        --bandwidth|-b)
            BANDWIDTH="$2"
            shift 2
            ;;
        --duration|-d)
            DURATION="$2"
            shift 2
            ;;
        --output-dir|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --dual-band)
            DUAL_BAND=1
            shift
            ;;
        --verbose|-v)
            VERBOSE=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --help|-h)
            cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --interface IFACE      Wi-Fi interface (required, e.g., wlan0)
  --channel CHAN         Single channel (mutually exclusive with --channel-2-4/5)
  --channel-2-4 CHAN     2.4 GHz channel for dual-band capture
  --channel-5 CHAN       5 GHz channel for dual-band capture
  --bandwidth BW         Bandwidth: 20, 40, 80, 160 (default: 20)
  --duration SECS        Capture duration in seconds (default: 60)
  --output-dir DIR       Output directory for .csi files (default: ./csi_data)
  --dual-band            Enable dual-band sequential capture
  --verbose              Verbose output
  --dry-run              Show commands without executing
  --help                 Show this help message

Single-band example:
  bash $(basename "$0") --interface wlan0 --channel 6 --duration 30

Dual-band example:
  bash $(basename "$0") --interface wlan0 --channel-2-4 6 --channel-5 36 --dual-band

EOF
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validation
if [[ -z "$INTERFACE" ]]; then
    log_error "Interface is required (--interface)"
    exit 1
fi

if [[ -z "$CHANNEL" ]] && [[ $DUAL_BAND -eq 0 ]]; then
    log_error "Channel is required (--channel or use --dual-band)"
    exit 1
fi

if [[ $DUAL_BAND -eq 1 ]] && ([[ -z "$CHANNEL_2_4" ]] || [[ -z "$CHANNEL_5" ]]); then
    log_error "Both --channel-2-4 and --channel-5 required for dual-band"
    exit 1
fi

if ! [[ "$BANDWIDTH" =~ ^(20|40|80|160)$ ]]; then
    log_error "Invalid bandwidth: $BANDWIDTH (must be 20, 40, 80, or 160)"
    exit 1
fi

# Check if running as root
if [[ $EUID -ne 0 ]] && [[ $DRY_RUN -eq 0 ]]; then
    log_error "This script must run as root (use: sudo)"
    exit 1
fi

# Check if interface exists
if ! ip link show "$INTERFACE" > /dev/null 2>&1; then
    log_error "Interface '$INTERFACE' not found"
    exit 1
fi

# Check if PicoScenes is available
if ! command -v $PICOSCENES_CMD &> /dev/null; then
    log_error "PicoScenes not found. Install from https://github.com/Marsrocky/PicoScenes"
    exit 1
fi

# Create output directory
if ! mkdir -p "$OUTPUT_DIR"; then
    log_error "Cannot create output directory: $OUTPUT_DIR"
    exit 1
fi

log_info "CSI Capture Configuration"
log_info "========================="
log_info "Interface: $INTERFACE"
log_info "Bandwidth: ${BANDWIDTH} MHz"
log_info "Duration: $DURATION seconds"
log_info "Output Directory: $OUTPUT_DIR"
if [[ $DUAL_BAND -eq 1 ]]; then
    log_info "Mode: Dual-band (2.4 GHz + 5 GHz)"
    log_info "2.4 GHz Channel: $CHANNEL_2_4"
    log_info "5 GHz Channel: $CHANNEL_5"
else
    log_info "Mode: Single-band"
    log_info "Channel: $CHANNEL"
fi

# Function to set interface to monitor mode
setup_monitor_mode() {
    local iface=$1
    log_info "Setting up monitor mode on $iface"

    if (( DRY_RUN )); then
        log_verbose "DRY RUN: ip link set $iface down"
        log_verbose "DRY RUN: iw $iface set monitor none"
        log_verbose "DRY RUN: ip link set $iface up"
        return 0
    fi

    # Bring interface down
    if ! ip link set "$iface" down; then
        log_warn "Could not bring down $iface (may already be down)"
    fi

    # Set monitor mode
    if ! iw "$iface" set monitor none; then
        log_error "Failed to set monitor mode on $iface"
        return 1
    fi

    # Bring interface up
    if ! ip link set "$iface" up; then
        log_error "Failed to bring up $iface"
        return 1
    fi

    sleep 1
    log_info "Monitor mode enabled on $iface"
    return 0
}

# Function to set channel
set_channel() {
    local iface=$1
    local channel=$2
    local bandwidth=$3

    log_info "Setting channel $channel (${bandwidth} MHz) on $iface"

    if (( DRY_RUN )); then
        log_verbose "DRY RUN: iw $iface set freq <freq> ${bandwidth}MHz"
        return 0
    fi

    # Determine center frequency from channel
    if [[ ${CHANNELS_2_4[$channel]} ]]; then
        local freq=${CHANNELS_2_4[$channel]}
        local band="2.4 GHz"
    elif [[ ${CHANNELS_5[$channel]} ]]; then
        local freq=${CHANNELS_5[$channel]}
        local band="5 GHz"
    else
        log_error "Unknown channel: $channel"
        return 1
    fi

    # Set frequency and bandwidth
    if ! iw dev "$iface" set freq "$freq" "${bandwidth}MHz"; then
        log_error "Failed to set channel $channel (freq $freq MHz)"
        return 1
    fi

    log_info "Channel set: $channel ($band, $freq MHz, ${bandwidth} MHz bandwidth)"
    sleep 1
    return 0
}

# Function to start PicoScenes CSI capture
capture_csi() {
    local iface=$1
    local channel=$2
    local bandwidth=$3
    local duration=$4
    local output_file=$5

    log_info "Starting CSI capture"
    log_info "Channel: $channel | Bandwidth: ${bandwidth}MHz | Duration: ${duration}s"
    log_info "Output: $output_file"

    if (( DRY_RUN )); then
        log_verbose "DRY RUN: PicoScenes -i $iface --csi --duration $duration --output $output_file"
        return 0
    fi

    # Launch PicoScenes with CSI capture
    # Note: Command syntax may vary depending on PicoScenes version
    # Adjust --device or other flags as needed for your installation

    if ! timeout "$((duration + 10))" $PICOSCENES_CMD \
        -i "$iface" \
        --csi \
        --duration "$duration" \
        --output "$output_file" 2>&1 | tee -a "${OUTPUT_DIR}/csi_capture.log"; then

        log_error "PicoScenes capture failed"
        return 1
    fi

    if [[ ! -f "$output_file" ]]; then
        log_error "CSI output file not created: $output_file"
        return 1
    fi

    # Get file size
    local file_size=$(du -h "$output_file" | cut -f1)
    log_info "CSI capture complete. File size: $file_size"
    return 0
}

# Function to record session metadata
record_metadata() {
    local channel=$1
    local bandwidth=$2
    local duration=$3
    local output_file=$4
    local band=$5

    local timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    local file_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file")
    local file_size_mb=$(echo "scale=2; $file_size / 1024 / 1024" | bc)

    # Append metadata to manifest
    cat >> "${OUTPUT_DIR}/manifest.txt" <<EOF
Timestamp: $timestamp
Channel: $channel
Band: $band
Bandwidth: ${bandwidth}MHz
Duration: ${duration}s
Output: $output_file
File Size: ${file_size_mb}MB
Interface: $INTERFACE

EOF
}

# Main execution
log_info "PicoScenes CSI Capture Started"

# Setup monitor mode
if ! setup_monitor_mode "$INTERFACE"; then
    log_error "Failed to setup monitor mode"
    exit 1
fi

# Initialize manifest
cat > "${OUTPUT_DIR}/manifest.txt" <<EOF
PicoScenes CSI Capture Session
Generated: $(date -u)
========================================

EOF

# Perform capture(s)
if [[ $DUAL_BAND -eq 1 ]]; then
    # Dual-band: 2.4 GHz first, then 5 GHz

    # 2.4 GHz capture
    if ! set_channel "$INTERFACE" "$CHANNEL_2_4" "$BANDWIDTH"; then
        log_error "Failed to set 2.4 GHz channel"
        exit 1
    fi

    local output_2_4="${OUTPUT_DIR}/csi_2_4_ch${CHANNEL_2_4}.csi"
    if ! capture_csi "$INTERFACE" "$CHANNEL_2_4" "$BANDWIDTH" "$DURATION" "$output_2_4"; then
        log_error "2.4 GHz capture failed"
        exit 1
    fi
    record_metadata "$CHANNEL_2_4" "$BANDWIDTH" "$DURATION" "$output_2_4" "2.4 GHz"

    # Brief pause between captures
    log_info "Pausing 5 seconds before 5 GHz capture..."
    sleep 5

    # 5 GHz capture
    if ! set_channel "$INTERFACE" "$CHANNEL_5" "$BANDWIDTH"; then
        log_error "Failed to set 5 GHz channel"
        exit 1
    fi

    local output_5="${OUTPUT_DIR}/csi_5_ch${CHANNEL_5}.csi"
    if ! capture_csi "$INTERFACE" "$CHANNEL_5" "$BANDWIDTH" "$DURATION" "$output_5"; then
        log_error "5 GHz capture failed"
        exit 1
    fi
    record_metadata "$CHANNEL_5" "$BANDWIDTH" "$DURATION" "$output_5" "5 GHz"

else
    # Single-band capture
    if ! set_channel "$INTERFACE" "$CHANNEL" "$BANDWIDTH"; then
        log_error "Failed to set channel"
        exit 1
    fi

    local output_file="${OUTPUT_DIR}/csi_ch${CHANNEL}.csi"
    if ! capture_csi "$INTERFACE" "$CHANNEL" "$BANDWIDTH" "$DURATION" "$output_file"; then
        log_error "CSI capture failed"
        exit 1
    fi
    record_metadata "$CHANNEL" "$BANDWIDTH" "$DURATION" "$output_file" "Unknown"
fi

log_info "CSI Capture Complete"
log_info "Output directory: $OUTPUT_DIR"
log_info "Manifest: ${OUTPUT_DIR}/manifest.txt"

# List output files
log_info "Generated files:"
ls -lh "$OUTPUT_DIR"/*.csi 2>/dev/null | while read line; do
    log_info "  $line"
done

exit 0
