#!/usr/bin/env python3
"""
Tri-band RSSI collector for Wi-Fi sensing research.

Collects RSSI measurements from 2.4 GHz, 5 GHz, and 6 GHz bands using an Intel
AX210, AX211, or similar Wi-Fi 6E tri-band card on Linux. Logs signal strength,
noise, SNR, bitrate, and latency metrics to a CSV file for frequency-differential
attenuation analysis.

Hardware Requirements:
  - Intel AX210, AX211, or similar Wi-Fi 6E tri-band card
  - iw and iwconfig command-line tools (iw-tools, wireless-tools packages)
  - ping command for latency measurement
  - Linux kernel with cfg80211 support and 6 GHz regulatory domain enabled

Usage:
    python3 dual_band_rssi_collector.py \\
        --interface wlan0 \\
        --target-ip 192.168.1.1 \\
        --output-file measurements.csv \\
        --interval 2 \\
        --trial-id trial_001 \\
        --phase-label baseline \\
        --material-class air \\
        --duration 60

CSV Schema:
    timestamp: ISO 8601 format (UTC)
    trial_id: Experiment identifier
    phase_label: Experiment phase (baseline, material_name, etc.)
    material_class: Classification of material between TX/RX
    band: 2.4 or 5 (GHz)
    channel: IEEE channel number
    frequency_mhz: Exact frequency in MHz
    rssi_dbm: Received Signal Strength Indicator (dBm)
    noise_dbm: Noise floor (dBm)
    snr_db: Signal-to-Noise Ratio (dB)
    tx_bitrate_mbps: Transmit bitrate (Mbps)
    rx_bitrate_mbps: Receive bitrate (Mbps)
    link_quality: Link quality (0-70 arbitrary units from iwconfig)
    ping_ms: Round-trip time to AP (milliseconds)
    ping_jitter_ms: Ping jitter (milliseconds)
    environment_id: Location/setup identifier
    notes: Optional notes field

Author: Wi-Fi Sensing Research Team
Version: 1.0.0
"""

import argparse
import csv
import logging
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dual_band_rssi_collector.log')
    ]
)
logger = logging.getLogger(__name__)


class RSSICollector:
    """Collects RSSI measurements from Wi-Fi interface."""

    # Frequency to channel mapping (2.4 GHz, 5 GHz, and 6 GHz bands)
    FREQ_TO_CHANNEL_2_4 = {
        2407: 0, 2412: 1, 2417: 2, 2422: 3, 2427: 4, 2432: 5, 2437: 6,
        2442: 7, 2447: 8, 2452: 9, 2457: 10, 2462: 11, 2467: 12, 2472: 13, 2484: 14
    }

    FREQ_TO_CHANNEL_5 = {
        5000: 0, 5160: 32, 5170: 34, 5180: 36, 5190: 38, 5200: 40, 5210: 42,
        5220: 44, 5230: 46, 5240: 48, 5250: 50, 5260: 52, 5270: 54, 5280: 56,
        5290: 58, 5300: 60, 5310: 62, 5320: 64, 5330: 66, 5340: 68, 5350: 70,
        5360: 72, 5370: 74, 5380: 76, 5390: 78, 5400: 80, 5410: 82, 5420: 84,
        5430: 86, 5440: 88, 5450: 90, 5460: 92, 5470: 94, 5480: 96, 5500: 100,
        5510: 102, 5520: 104, 5530: 106, 5540: 108, 5550: 110, 5560: 112, 5570: 114,
        5580: 116, 5590: 118, 5600: 120, 5610: 122, 5620: 124, 5630: 126, 5640: 128,
        5650: 130, 5660: 132, 5670: 134, 5680: 136, 5690: 138, 5700: 140, 5710: 142,
        5720: 144, 5745: 149, 5755: 151, 5765: 153, 5775: 155, 5785: 157, 5795: 159,
        5805: 161, 5815: 163, 5825: 165, 5835: 167, 5845: 169, 5855: 171, 5865: 173,
        5875: 175, 5885: 177
    }

    # 6 GHz band: UNII-5 through UNII-8 (5.925 - 7.125 GHz)
    # Channels 1-233, 20 MHz spacing, center frequencies starting at 5955 MHz
    FREQ_TO_CHANNEL_6 = {
        5955: 1, 5975: 5, 5995: 9, 6015: 13, 6035: 17, 6055: 21, 6075: 25,
        6095: 29, 6115: 33, 6135: 37, 6155: 41, 6175: 45, 6195: 49, 6215: 53,
        6235: 57, 6255: 61, 6275: 65, 6295: 69, 6315: 73, 6335: 77, 6355: 81,
        6375: 85, 6395: 89, 6415: 93, 6435: 97, 6455: 101, 6475: 105, 6495: 109,
        6515: 113, 6535: 117, 6555: 121, 6575: 125, 6595: 129, 6615: 133,
        6635: 137, 6655: 141, 6675: 145, 6695: 149, 6715: 153, 6735: 157,
        6755: 161, 6775: 165, 6795: 169, 6815: 173, 6835: 177, 6855: 181,
        6875: 185, 6895: 189, 6915: 193, 6935: 197, 6955: 201, 6975: 205,
        6995: 209, 7015: 213, 7035: 217, 7055: 221, 7075: 225, 7095: 229,
        7115: 233
    }

    def __init__(self, interface: str, target_ip: str, environment_id: str = "unknown"):
        """
        Initialize the RSSI collector.

        Args:
            interface: Network interface name (e.g., 'wlan0')
            target_ip: IP address of the Access Point for ping measurements
            environment_id: Location or setup identifier
        """
        self.interface = interface
        self.target_ip = target_ip
        self.environment_id = environment_id
        self.last_ping = None
        self.last_ping_jitter = None

    def _run_command(self, cmd: str) -> Optional[str]:
        """
        Execute a shell command and return stdout.

        Args:
            cmd: Command string to execute

        Returns:
            Command output as string, or None if command fails
        """
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout if result.returncode == 0 else None
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out: {cmd}")
            return None
        except Exception as e:
            logger.warning(f"Command failed ({cmd}): {e}")
            return None

    def _parse_iw_link(self) -> Dict[str, any]:
        """
        Parse output from 'iw dev <interface> link' command.

        Returns:
            Dictionary with keys: frequency_mhz, rssi_dbm, tx_bitrate_mbps,
            rx_bitrate_mbps, signal_dbm, frequency_khz
        """
        output = self._run_command(f"iw dev {self.interface} link")
        if not output:
            return {}

        data = {}
        for line in output.split('\n'):
            line = line.strip()

            # Parse frequency
            if 'freq' in line.lower():
                match = re.search(r'(\d+)\s*MHz', line)
                if match:
                    data['frequency_mhz'] = int(match.group(1))

            # Parse signal strength
            if 'signal' in line.lower() or 'strength' in line.lower():
                match = re.search(r'(-\d+)\s*dBm', line)
                if match:
                    data['rssi_dbm'] = int(match.group(1))
                    data['signal_dbm'] = int(match.group(1))

            # Parse TX bitrate
            if 'tx bitrate' in line.lower():
                match = re.search(r'(\d+(?:\.\d+)?)\s*Mbit', line)
                if match:
                    data['tx_bitrate_mbps'] = float(match.group(1))

            # Parse RX bitrate
            if 'rx bitrate' in line.lower():
                match = re.search(r'(\d+(?:\.\d+)?)\s*Mbit', line)
                if match:
                    data['rx_bitrate_mbps'] = float(match.group(1))

        return data

    def _parse_iwconfig(self) -> Dict[str, any]:
        """
        Parse output from 'iwconfig <interface>' command as fallback.

        Returns:
            Dictionary with keys: rssi_dbm, link_quality, noise_dbm
        """
        output = self._run_command(f"iwconfig {self.interface}")
        if not output:
            return {}

        data = {}
        for line in output.split('\n'):
            line = line.strip()

            # Parse signal level (RSSI alternative)
            if 'signal level' in line.lower():
                # Format: "Signal level=-50 dBm"
                match = re.search(r'=(-?\d+)\s*dBm', line)
                if match:
                    data['rssi_dbm'] = int(match.group(1))

            # Parse link quality
            if 'link quality' in line.lower():
                # Format: "Link Quality=70/70"
                match = re.search(r'(\d+)/\d+', line)
                if match:
                    data['link_quality'] = int(match.group(1))

            # Parse noise level
            if 'noise level' in line.lower():
                match = re.search(r'=(-?\d+)\s*dBm', line)
                if match:
                    data['noise_dbm'] = int(match.group(1))

        return data

    def _parse_iw_station(self) -> Dict[str, any]:
        """
        Parse output from 'iw dev <interface> station dump' command.

        Returns:
            Dictionary with keys from station stats (signal, expected throughput, etc.)
        """
        output = self._run_command(f"iw dev {self.interface} station dump")
        if not output:
            return {}

        data = {}
        for line in output.split('\n'):
            line = line.strip()

            # Parse signal (RSSI)
            if line.startswith('signal:'):
                match = re.search(r'(-\d+)\s*dBm', line)
                if match:
                    data['rssi_dbm'] = int(match.group(1))

            # Parse signal avg (smoothed RSSI)
            if line.startswith('signal avg:'):
                match = re.search(r'(-\d+)\s*dBm', line)
                if match:
                    data['rssi_dbm_avg'] = int(match.group(1))

            # Parse rx bitrate
            if line.startswith('rx bitrate:'):
                match = re.search(r'(\d+(?:\.\d+)?)\s*Mbit', line)
                if match:
                    data['rx_bitrate_mbps'] = float(match.group(1))

            # Parse tx bitrate
            if line.startswith('tx bitrate:'):
                match = re.search(r'(\d+(?:\.\d+)?)\s*Mbit', line)
                if match:
                    data['tx_bitrate_mbps'] = float(match.group(1))

        return data

    def _measure_ping(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Measure round-trip time to the Access Point.

        Returns:
            Tuple of (ping_ms, jitter_ms) or (None, None) if measurement fails
        """
        try:
            # Send 3 pings, extract RTT and jitter
            result = subprocess.run(
                f"ping -c 3 -W 2 {self.target_ip}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None, None

            output = result.stdout
            # Look for "round-trip min/avg/max/stddev" line
            match = re.search(r'min/avg/max/stddev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', output)
            if match:
                avg_rtt = float(match.group(2))
                jitter = float(match.group(4))
                self.last_ping = avg_rtt
                self.last_ping_jitter = jitter
                return avg_rtt, jitter

            return None, None
        except Exception as e:
            logger.debug(f"Ping measurement failed: {e}")
            return None, None

    def _freq_to_band(self, frequency_mhz: int) -> Optional[float]:
        """
        Determine band (2.4, 5, or 6 GHz) from frequency in MHz.

        Args:
            frequency_mhz: Frequency in MHz

        Returns:
            2.4, 5, or 6 (GHz), or None if unrecognized
        """
        if 2400 <= frequency_mhz < 2500:
            return 2.4
        elif 5000 <= frequency_mhz < 5925:
            return 5
        elif 5925 <= frequency_mhz < 7125:
            return 6
        return None

    def _freq_to_channel(self, frequency_mhz: int) -> Optional[int]:
        """
        Look up IEEE channel number from frequency.

        Args:
            frequency_mhz: Frequency in MHz

        Returns:
            Channel number or None if not found
        """
        if frequency_mhz in self.FREQ_TO_CHANNEL_2_4:
            return self.FREQ_TO_CHANNEL_2_4[frequency_mhz]
        elif frequency_mhz in self.FREQ_TO_CHANNEL_5:
            return self.FREQ_TO_CHANNEL_5[frequency_mhz]
        elif frequency_mhz in self.FREQ_TO_CHANNEL_6:
            return self.FREQ_TO_CHANNEL_6[frequency_mhz]
        return None

    def collect(self) -> Dict[str, any]:
        """
        Collect a single measurement from the Wi-Fi interface.

        Attempts to gather data from multiple sources (iw link, iwconfig, iw station)
        and merges results with preference for more reliable sources.

        Returns:
            Dictionary with all collected metrics
        """
        measurement = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'interface': self.interface,
            'environment_id': self.environment_id,
        }

        # Collect from iw link (most reliable)
        iw_link_data = self._parse_iw_link()
        measurement.update(iw_link_data)

        # Collect from iw station dump (alternative source)
        iw_station_data = self._parse_iw_station()
        # Don't overwrite iw_link data
        for key, value in iw_station_data.items():
            if key not in measurement or measurement[key] is None:
                measurement[key] = value

        # Collect from iwconfig (fallback)
        iwconfig_data = self._parse_iwconfig()
        for key, value in iwconfig_data.items():
            if key not in measurement or measurement[key] is None:
                measurement[key] = value

        # Derive channel from frequency if we have it
        if 'frequency_mhz' in measurement and measurement['frequency_mhz']:
            measurement['channel'] = self._freq_to_channel(measurement['frequency_mhz'])
            measurement['band'] = self._freq_to_band(measurement['frequency_mhz'])

        # Calculate SNR if we have RSSI and noise
        if 'rssi_dbm' in measurement and 'noise_dbm' in measurement:
            if measurement['rssi_dbm'] and measurement['noise_dbm']:
                measurement['snr_db'] = measurement['rssi_dbm'] - measurement['noise_dbm']

        # Measure ping latency
        ping_ms, ping_jitter_ms = self._measure_ping()
        if ping_ms is not None:
            measurement['ping_ms'] = round(ping_ms, 2)
        if ping_jitter_ms is not None:
            measurement['ping_jitter_ms'] = round(ping_jitter_ms, 2)

        return measurement


def main():
    """Parse arguments and run RSSI collection loop."""
    parser = argparse.ArgumentParser(
        description='Collect dual-band RSSI measurements from Wi-Fi interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect for 60 seconds, 2-second intervals
  python3 dual_band_rssi_collector.py \\
    --interface wlan0 --target-ip 192.168.1.1 \\
    --output-file baseline.csv --trial-id trial_001 \\
    --phase-label baseline --material-class air --duration 60

  # Collect with specific material and environment
  python3 dual_band_rssi_collector.py \\
    --interface wlan0 --target-ip 192.168.1.1 \\
    --output-file wood.csv --trial-id trial_001 \\
    --phase-label material_test --material-class wood \\
    --environment-id lab_1 --interval 1 --duration 120
        """
    )

    parser.add_argument(
        '--interface', '-i',
        required=True,
        help='Wi-Fi interface name (e.g., wlan0)'
    )
    parser.add_argument(
        '--target-ip', '-t',
        required=True,
        help='IP address of the Access Point for ping measurements'
    )
    parser.add_argument(
        '--output-file', '-o',
        required=True,
        help='Output CSV file path'
    )
    parser.add_argument(
        '--interval', '-n',
        type=float,
        default=2,
        help='Measurement interval in seconds (default: 2)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=float,
        default=None,
        help='Total collection duration in seconds (optional; runs indefinitely if not specified)'
    )
    parser.add_argument(
        '--trial-id', '-T',
        required=True,
        help='Trial/experiment identifier'
    )
    parser.add_argument(
        '--phase-label', '-p',
        required=True,
        help='Phase label (e.g., baseline, material_1)'
    )
    parser.add_argument(
        '--material-class', '-m',
        required=True,
        help='Material classification (e.g., air, wood, concrete)'
    )
    parser.add_argument(
        '--environment-id', '-e',
        default='unknown',
        help='Environment/location identifier (default: unknown)'
    )
    parser.add_argument(
        '--notes', '-N',
        default='',
        help='Optional notes field'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.interval <= 0:
        logger.error("Interval must be positive")
        sys.exit(1)

    if args.duration is not None and args.duration <= 0:
        logger.error("Duration must be positive")
        sys.exit(1)

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize collector
    collector = RSSICollector(
        interface=args.interface,
        target_ip=args.target_ip,
        environment_id=args.environment_id
    )

    logger.info(
        f"Starting RSSI collection on {args.interface} "
        f"(target AP: {args.target_ip}, interval: {args.interval}s)"
    )

    # Determine if file is new (for CSV header)
    file_exists = output_path.exists()

    csv_fieldnames = [
        'timestamp', 'trial_id', 'phase_label', 'material_class', 'band',
        'channel', 'frequency_mhz', 'rssi_dbm', 'noise_dbm', 'snr_db',
        'tx_bitrate_mbps', 'rx_bitrate_mbps', 'link_quality', 'ping_ms',
        'ping_jitter_ms', 'environment_id', 'notes'
    ]

    # Collection loop
    start_time = time.time()
    measurement_count = 0

    try:
        with open(output_path, 'a', newline='') as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=csv_fieldnames,
                restval='',
                extrasaction='ignore'
            )

            # Write header only for new file
            if not file_exists:
                writer.writeheader()
                logger.info(f"Created new CSV file: {output_path}")

            while True:
                # Check if duration exceeded
                if args.duration and (time.time() - start_time) > args.duration:
                    logger.info(
                        f"Duration limit ({args.duration}s) reached. Stopping collection."
                    )
                    break

                # Collect measurement
                measurement = collector.collect()

                # Add metadata
                measurement['trial_id'] = args.trial_id
                measurement['phase_label'] = args.phase_label
                measurement['material_class'] = args.material_class
                measurement['notes'] = args.notes

                # Write to CSV
                writer.writerow(measurement)
                csvfile.flush()
                measurement_count += 1

                if measurement_count % 10 == 0:
                    logger.info(
                        f"Collected {measurement_count} measurements "
                        f"(RSSI: {measurement.get('rssi_dbm', 'N/A')} dBm, "
                        f"Band: {measurement.get('band', 'N/A')} GHz)"
                    )

                # Sleep until next measurement
                time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
    except Exception as e:
        logger.error(f"Error during collection: {e}", exc_info=True)
        sys.exit(1)

    logger.info(
        f"Collection complete. Wrote {measurement_count} measurements to {output_path}"
    )


if __name__ == '__main__':
    main()
