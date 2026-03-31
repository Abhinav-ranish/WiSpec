#!/usr/bin/env python3
"""
Comprehensive experiment controller for tri-band RSSI measurements.

Orchestrates multi-phase Wi-Fi sensing experiments with automatic transitions between
material samples, support for single-band, dual-band, and tri-band (2.4 + 5 + 6 GHz)
collection modes, and experiment metadata logging.

Features:
  - Defines and manages experiment phases (baseline, material tests, etc.)
  - User prompts between phases for manual material placement
  - Launches dual_band_rssi_collector.py subprocess for each phase
  - Supports 2.4 GHz, dual-band (2.4 + 5 GHz), and tri-band (2.4 + 5 + 6 GHz) modes
  - Records comprehensive experiment metadata (date, location, conditions, etc.)
  - Generates experiment manifest JSON with file references
  - Resume capability: allows resuming from a specified phase if interrupted
  - Validates AP connectivity before starting

Usage:
    # Run full experiment with all materials
    python3 experiment_controller.py \\
        --experiment-id exp_001 \\
        --materials "air,wood,concrete,drywall" \\
        --duration-per-phase 120 \\
        --ap-ip 192.168.1.1 \\
        --ap-interface wlan0 \\
        --location "Lab A, Table 1" \\
        --distance-cm 50

    # Run dual-band experiment (2.4 GHz + 5 GHz)
    python3 experiment_controller.py \\
        --experiment-id exp_dual \\
        --materials "baseline,wood,concrete" \\
        --duration-per-phase 60 \\
        --ap-ip 192.168.1.1 \\
        --ap-interface wlan0 \\
        --dual-band \\
        --ssid-2-4 MyNetwork-2G \\
        --ssid-5 MyNetwork-5G

    # Run tri-band experiment (2.4 GHz + 5 GHz + 6 GHz)
    python3 experiment_controller.py \\
        --experiment-id exp_tri \\
        --materials "baseline,wood,concrete" \\
        --duration-per-phase 60 \\
        --ap-ip 192.168.1.1 \\
        --ap-interface wlan0 \\
        --tri-band \\
        --ssid-2-4 MyNetwork-2G \\
        --ssid-5 MyNetwork-5G \\
        --ssid-6 MyNetwork-6G

    # Resume from phase 3 (wood)
    python3 experiment_controller.py \\
        --experiment-id exp_001 \\
        --resume-phase 3

Manifest File Schema (JSON):
    {
      "experiment_id": "exp_001",
      "start_time": "2026-03-21T10:30:00Z",
      "end_time": "2026-03-21T11:45:00Z",
      "duration_seconds": 4500,
      "location": "Lab A, Table 1",
      "distance_cm": 50,
      "temperature_c": 22.5,
      "humidity_percent": 45,
      "ap_model": "Xiaomi Mi Router 4C",
      "ap_interface": "wlan0",
      "ap_ip": "192.168.1.1",
      "client_interface": "wlan0",
      "dual_band": true,
      "tri_band": true,
      "ssid_2_4": "MyNetwork-2G",
      "ssid_5": "MyNetwork-5G",
      "ssid_6": "MyNetwork-6G",
      "phases": [
        {
          "phase_id": 0,
          "label": "baseline",
          "material_class": "air",
          "duration_seconds": 120,
          "start_time": "2026-03-21T10:30:00Z",
          "csv_file": "baseline.csv",
          "notes": "No obstruction between TX and RX"
        },
        ...
      ]
    }

Author: Wi-Fi Sensing Research Team
Version: 1.0.0
"""

import argparse
import csv
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('experiment_controller.log')
    ]
)
logger = logging.getLogger(__name__)


class ExperimentController:
    """Orchestrates multi-phase RSSI measurement experiments."""

    def __init__(
        self,
        experiment_id: str,
        materials: List[str],
        duration_per_phase: int,
        ap_ip: str,
        ap_interface: str,
        client_interface: str = 'wlan0',
        output_dir: Optional[str] = None,
        dual_band: bool = False,
        tri_band: bool = False,
        ssid_2_4: Optional[str] = None,
        ssid_5: Optional[str] = None,
        ssid_6: Optional[str] = None,
        environment_id: str = 'unknown',
        location: str = 'unknown',
        distance_cm: Optional[float] = None,
        temperature_c: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        ap_model: str = 'unknown'
    ):
        """
        Initialize experiment controller.

        Args:
            experiment_id: Unique identifier for this experiment
            materials: List of material names (first is always baseline/air)
            duration_per_phase: Duration per phase in seconds
            ap_ip: IP address of the Access Point
            ap_interface: Interface on the AP (for logging)
            client_interface: Client Wi-Fi interface (default: wlan0)
            output_dir: Output directory for CSV and manifest files
            dual_band: Enable dual-band (2.4 + 5 GHz) collection
            tri_band: Enable tri-band (2.4 + 5 + 6 GHz) collection
            ssid_2_4: SSID for 2.4 GHz band (if dual_band or tri_band=True)
            ssid_5: SSID for 5 GHz band (if dual_band or tri_band=True)
            ssid_6: SSID for 6 GHz band (if tri_band=True)
            environment_id: Environment identifier
            location: Physical location description
            distance_cm: Distance between TX and RX in cm
            temperature_c: Room temperature in Celsius
            humidity_percent: Humidity percentage
            ap_model: Access Point model name
        """
        self.experiment_id = experiment_id
        self.materials = materials
        self.duration_per_phase = duration_per_phase
        self.ap_ip = ap_ip
        self.ap_interface = ap_interface
        self.client_interface = client_interface
        self.dual_band = dual_band
        self.tri_band = tri_band
        self.ssid_2_4 = ssid_2_4
        self.ssid_5 = ssid_5
        self.ssid_6 = ssid_6
        self.environment_id = environment_id
        self.location = location
        self.distance_cm = distance_cm
        self.temperature_c = temperature_c
        self.humidity_percent = humidity_percent
        self.ap_model = ap_model

        # Set output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(f"experiment_{experiment_id}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Experiment state
        self.phases = []
        self.start_time = None
        self.end_time = None
        self._collector_process = None

    def _validate_connectivity(self) -> bool:
        """
        Check if Access Point is reachable.

        Returns:
            True if AP responds to ping, False otherwise
        """
        try:
            result = subprocess.run(
                f"ping -c 1 -W 2 {self.ap_ip}",
                shell=True,
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")
            return False

    def _get_current_wifi_info(self) -> Dict[str, any]:
        """
        Retrieve current connected Wi-Fi network information.

        Returns:
            Dictionary with ssid, frequency, channel info
        """
        info = {}
        try:
            # Get current SSID via iwconfig
            result = subprocess.run(
                f"iwconfig {self.client_interface}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=3
            )
            if 'SSID:' in result.stdout:
                import re
                match = re.search(r'SSID:"([^"]*)"', result.stdout)
                if match:
                    info['current_ssid'] = match.group(1)
        except Exception as e:
            logger.debug(f"Could not retrieve Wi-Fi info: {e}")

        return info

    def setup_phases(self):
        """
        Define phases for the experiment.

        First phase is always "baseline" (air / no obstruction).
        Subsequent phases are named after each material.
        """
        self.phases = []

        # Baseline phase (always first)
        self.phases.append({
            'phase_id': 0,
            'label': 'baseline',
            'material_class': 'air',
            'duration_seconds': self.duration_per_phase,
            'csv_file': 'baseline.csv',
            'notes': 'No obstruction between TX and RX'
        })

        # Material phases
        for idx, material in enumerate(self.materials[1:], start=1):
            self.phases.append({
                'phase_id': idx,
                'label': f'material_{idx}',
                'material_class': material,
                'duration_seconds': self.duration_per_phase,
                'csv_file': f'{material}.csv',
                'notes': f'Testing with {material} between TX and RX'
            })

        logger.info(f"Setup {len(self.phases)} phases: {[p['label'] for p in self.phases]}")

    def prompt_for_phase(self, phase: Dict) -> bool:
        """
        Prompt user to prepare for the next phase.

        Args:
            phase: Phase dictionary

        Returns:
            True if user is ready, False if user canceled
        """
        material = phase['material_class']
        phase_label = phase['label']

        if material == 'air':
            prompt = f"\n{'='*60}\nPhase: {phase_label} ({material})\nRemove all obstructions between TX and RX.\nPress ENTER when ready (or 'q' to quit): "
        else:
            prompt = f"\n{'='*60}\nPhase: {phase_label} ({material})\nPlace {material} between TX and RX.\nPress ENTER when ready (or 'q' to quit): "

        response = input(prompt).strip().lower()
        return response != 'q'

    def run_phase(self, phase: Dict) -> bool:
        """
        Execute a single measurement phase.

        Launches dual_band_rssi_collector.py as a subprocess and monitors execution.

        Args:
            phase: Phase dictionary

        Returns:
            True if phase completed successfully, False otherwise
        """
        csv_file = self.output_dir / phase['csv_file']
        phase_label = phase['label']
        material_class = phase['material_class']
        duration = phase['duration_seconds']

        logger.info(f"Starting phase: {phase_label} ({material_class})")
        logger.info(f"Duration: {duration}s, Output: {csv_file}")

        # Build collector command
        collector_script = Path(__file__).parent / 'dual_band_rssi_collector.py'

        if not collector_script.exists():
            logger.error(f"Collector script not found: {collector_script}")
            return False

        cmd = [
            'python3', str(collector_script),
            '--interface', self.client_interface,
            '--target-ip', self.ap_ip,
            '--output-file', str(csv_file),
            '--interval', '2',
            '--duration', str(duration),
            '--trial-id', self.experiment_id,
            '--phase-label', phase_label,
            '--material-class', material_class,
            '--environment-id', self.environment_id,
            '--notes', phase['notes']
        ]

        try:
            # Launch subprocess
            self._collector_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Monitor process
            start_time = time.time()
            while True:
                returncode = self._collector_process.poll()

                if returncode is not None:
                    # Process finished
                    if returncode == 0:
                        logger.info(f"Phase completed: {phase_label}")
                        phase['end_time'] = datetime.utcnow().isoformat() + 'Z'
                        return True
                    else:
                        stdout, stderr = self._collector_process.communicate()
                        logger.error(
                            f"Collector process exited with code {returncode}\n"
                            f"stdout: {stdout}\nstderr: {stderr}"
                        )
                        return False

                # Check if duration exceeded (with buffer)
                elapsed = time.time() - start_time
                if elapsed > duration + 10:
                    logger.warning(
                        f"Phase duration exceeded ({elapsed:.1f}s > {duration}s). "
                        "Terminating collector."
                    )
                    self._collector_process.terminate()
                    self._collector_process.wait(timeout=5)
                    return False

                time.sleep(1)

        except KeyboardInterrupt:
            logger.warning("Phase interrupted by user")
            if self._collector_process:
                self._collector_process.terminate()
                self._collector_process.wait()
            return False
        except Exception as e:
            logger.error(f"Error running phase: {e}", exc_info=True)
            if self._collector_process:
                self._collector_process.terminate()
            return False

    def run_experiment(self, start_phase: int = 0) -> bool:
        """
        Execute the full experiment, starting from a specified phase.

        Args:
            start_phase: Phase index to start from (0 = baseline, default)

        Returns:
            True if experiment completed, False if aborted
        """
        if start_phase >= len(self.phases):
            logger.error(f"Invalid start phase: {start_phase}")
            return False

        # Validate connectivity
        logger.info(f"Validating connectivity to AP ({self.ap_ip})...")
        if not self._validate_connectivity():
            logger.error("Cannot reach Access Point. Check IP address and AP status.")
            return False
        logger.info("AP connectivity verified")

        # Log Wi-Fi info
        wifi_info = self._get_current_wifi_info()
        if 'current_ssid' in wifi_info:
            logger.info(f"Connected to: {wifi_info['current_ssid']}")

        self.start_time = datetime.utcnow().isoformat() + 'Z'
        logger.info(f"Experiment started: {self.start_time}")

        # Run phases
        for phase_idx in range(start_phase, len(self.phases)):
            phase = self.phases[phase_idx]

            # Prompt user
            if not self.prompt_for_phase(phase):
                logger.info("Experiment canceled by user")
                return False

            # Record phase start time
            phase['start_time'] = datetime.utcnow().isoformat() + 'Z'

            # Run phase
            if not self.run_phase(phase):
                logger.error(f"Phase failed: {phase['label']}")
                return False

            # Brief pause between phases
            if phase_idx < len(self.phases) - 1:
                logger.info("Waiting 5s before next phase...")
                time.sleep(5)

        self.end_time = datetime.utcnow().isoformat() + 'Z'
        logger.info(f"Experiment completed: {self.end_time}")
        return True

    def save_manifest(self):
        """Save experiment metadata and file references to JSON manifest."""
        manifest = {
            'experiment_id': self.experiment_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'location': self.location,
            'distance_cm': self.distance_cm,
            'temperature_c': self.temperature_c,
            'humidity_percent': self.humidity_percent,
            'ap_model': self.ap_model,
            'ap_ip': self.ap_ip,
            'ap_interface': self.ap_interface,
            'client_interface': self.client_interface,
            'dual_band': self.dual_band,
            'tri_band': self.tri_band,
            'ssid_2_4': self.ssid_2_4,
            'ssid_5': self.ssid_5,
            'ssid_6': self.ssid_6,
            'environment_id': self.environment_id,
            'phases': self.phases
        }

        # Calculate total duration
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
            manifest['duration_seconds'] = int((end - start).total_seconds())

        manifest_file = self.output_dir / f"{self.experiment_id}_manifest.json"

        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest saved: {manifest_file}")

    def summary(self):
        """Print experiment summary."""
        print("\n" + "="*60)
        print("EXPERIMENT SUMMARY")
        print("="*60)
        print(f"Experiment ID: {self.experiment_id}")
        print(f"Output Directory: {self.output_dir}")
        print(f"Start Time: {self.start_time}")
        print(f"End Time: {self.end_time}")
        print(f"Location: {self.location}")
        print(f"Distance: {self.distance_cm} cm")
        print(f"AP Model: {self.ap_model}")
        print(f"Dual-Band: {self.dual_band}")
        print(f"Tri-Band: {self.tri_band}")
        print(f"Phases: {len(self.phases)}")
        for phase in self.phases:
            status = "✓" if phase.get('end_time') else "✗"
            print(f"  {status} {phase['label']}: {phase['csv_file']}")
        print("="*60 + "\n")


def main():
    """Parse arguments and run experiment."""
    parser = argparse.ArgumentParser(
        description='Orchestrate multi-phase dual-band RSSI experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic single-band experiment (2.4 GHz)
  python3 experiment_controller.py \\
    --experiment-id exp_001 \\
    --materials "air,wood,concrete,drywall" \\
    --duration-per-phase 120 \\
    --ap-ip 192.168.1.1 \\
    --location "Lab A, Table 1" \\
    --distance-cm 50

  # Dual-band experiment with separate SSIDs
  python3 experiment_controller.py \\
    --experiment-id exp_dual \\
    --materials "baseline,wood,concrete" \\
    --duration-per-phase 60 \\
    --ap-ip 192.168.1.1 \\
    --dual-band \\
    --ssid-2-4 MyNetwork-2G \\
    --ssid-5 MyNetwork-5G \\
    --location "Lab B" \\
    --distance-cm 30

  # Resume experiment from phase 2
  python3 experiment_controller.py \\
    --experiment-id exp_001 \\
    --resume-phase 2
        """
    )

    parser.add_argument(
        '--experiment-id', '-e',
        required=True,
        help='Unique experiment identifier'
    )
    parser.add_argument(
        '--materials', '-m',
        type=lambda x: [s.strip() for s in x.split(',')],
        default=['air'],
        help='Comma-separated list of materials (first is baseline/air)'
    )
    parser.add_argument(
        '--duration-per-phase', '-d',
        type=int,
        default=120,
        help='Duration per phase in seconds (default: 120)'
    )
    parser.add_argument(
        '--ap-ip',
        required=True,
        help='IP address of the Access Point'
    )
    parser.add_argument(
        '--ap-interface',
        default='wlan0',
        help='Interface name on the AP (for logging, default: wlan0)'
    )
    parser.add_argument(
        '--client-interface', '-i',
        default='wlan0',
        help='Client Wi-Fi interface (default: wlan0)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for results (default: experiment_<id>)'
    )
    parser.add_argument(
        '--dual-band',
        action='store_true',
        help='Enable dual-band (2.4 + 5 GHz) collection'
    )
    parser.add_argument(
        '--tri-band',
        action='store_true',
        help='Enable tri-band (2.4 + 5 + 6 GHz) collection (requires Wi-Fi 6E hardware)'
    )
    parser.add_argument(
        '--ssid-2-4',
        help='SSID for 2.4 GHz band (required if --dual-band or --tri-band)'
    )
    parser.add_argument(
        '--ssid-5',
        help='SSID for 5 GHz band (required if --dual-band or --tri-band)'
    )
    parser.add_argument(
        '--ssid-6',
        help='SSID for 6 GHz band (required if --tri-band)'
    )
    parser.add_argument(
        '--location',
        default='unknown',
        help='Physical location description'
    )
    parser.add_argument(
        '--distance-cm',
        type=float,
        help='Distance between TX and RX in centimeters'
    )
    parser.add_argument(
        '--temperature-c',
        type=float,
        help='Room temperature in Celsius'
    )
    parser.add_argument(
        '--humidity-percent',
        type=float,
        help='Room humidity in percent'
    )
    parser.add_argument(
        '--ap-model',
        default='unknown',
        help='Access Point model name'
    )
    parser.add_argument(
        '--environment-id',
        default='unknown',
        help='Environment identifier'
    )
    parser.add_argument(
        '--resume-phase',
        type=int,
        default=0,
        help='Resume from this phase index (0 = baseline)'
    )

    args = parser.parse_args()

    # Validate dual-band and tri-band args
    if args.tri_band:
        args.dual_band = True  # tri-band implies dual-band
        if not args.ssid_2_4 or not args.ssid_5 or not args.ssid_6:
            logger.error("--ssid-2-4, --ssid-5, and --ssid-6 are required when --tri-band is set")
            sys.exit(1)
    elif args.dual_band:
        if not args.ssid_2_4 or not args.ssid_5:
            logger.error("--ssid-2-4 and --ssid-5 are required when --dual-band is set")
            sys.exit(1)

    # Create controller
    controller = ExperimentController(
        experiment_id=args.experiment_id,
        materials=args.materials,
        duration_per_phase=args.duration_per_phase,
        ap_ip=args.ap_ip,
        ap_interface=args.ap_interface,
        client_interface=args.client_interface,
        output_dir=args.output_dir,
        dual_band=args.dual_band,
        tri_band=args.tri_band,
        ssid_2_4=args.ssid_2_4,
        ssid_5=args.ssid_5,
        ssid_6=getattr(args, 'ssid_6', None),
        environment_id=args.environment_id,
        location=args.location,
        distance_cm=args.distance_cm,
        temperature_c=args.temperature_c,
        humidity_percent=args.humidity_percent,
        ap_model=args.ap_model
    )

    # Setup and run
    controller.setup_phases()

    if controller.run_experiment(start_phase=args.resume_phase):
        controller.save_manifest()
        controller.summary()
        logger.info("Experiment completed successfully")
    else:
        logger.warning("Experiment did not complete")
        controller.save_manifest()  # Save partial results
        sys.exit(1)


if __name__ == '__main__':
    main()
