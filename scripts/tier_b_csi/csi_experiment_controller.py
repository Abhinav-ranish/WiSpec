#!/usr/bin/env python3
"""
Comprehensive CSI Experiment Controller for Dual-Band Wi-Fi Sensing.

Orchestrates multi-phase Channel State Information (CSI) collection at 2.4 GHz and 5 GHz
using PicoScenes on Intel AX200/AX210 hardware. Manages material placement phases, CSI
capture sequencing, and generates complete experiment manifests with file references.

Features:
  - Phase-based material testing (baseline, wood, concrete, etc.)
  - Dual-band sequential CSI capture (2.4 GHz → 5 GHz for each phase)
  - Automatic channel configuration and PicoScenes invocation
  - Comprehensive experiment metadata logging
  - CSI file tracking with frame/subcarrier information
  - Resume capability for interrupted captures
  - Automatic PicoScenes output post-processing (when available)

CSI Tiers (from PicoScenes):
  Tier 1 (RSSI): Signal strength only (all hardware)
  Tier 2 (CSI): Per-subcarrier channel estimates (AX200+, limited devices)
  Tier 3 (Sounding): Structured sounding measurements (research-grade hardware)

Hardware Requirements:
  - Intel AX200 or AX210 M.2 Wi-Fi card
  - PicoScenes installed and functioning
  - Linux kernel 5.4+ with cfg80211
  - Root/sudo privileges
  - 2+ GB storage per 60-second CSI capture session

CSI Usage Example:
    # Run full dual-band CSI experiment with materials
    python3 csi_experiment_controller.py \\
        --experiment-id csi_exp_001 \\
        --materials "baseline,wood,concrete,drywall" \\
        --duration-per-band 30 \\
        --interface wlan0 \\
        --channel-2-4 6 \\
        --channel-5 36 \\
        --bandwidth 20 \\
        --location "Lab A" \\
        --distance-cm 50

    # Resume from specific phase
    python3 csi_experiment_controller.py \\
        --experiment-id csi_exp_001 \\
        --resume-phase 2

Manifest Schema (JSON):
    {
      "experiment_id": "csi_exp_001",
      "start_time": "2026-03-21T10:30:00Z",
      "end_time": "2026-03-21T11:45:00Z",
      "duration_seconds": 4500,
      "location": "Lab A",
      "distance_cm": 50,
      "temperature_c": 22.5,
      "humidity_percent": 45,
      "interface": "wlan0",
      "bandwidth": "20 MHz",
      "frequency_2_4_mhz": 2437,
      "frequency_5_mhz": 5180,
      "channel_2_4": 6,
      "channel_5": 36,
      "phases": [
        {
          "phase_id": 0,
          "label": "baseline",
          "material_class": "air",
          "duration_seconds": 30,
          "start_time": "2026-03-21T10:30:00Z",
          "end_time": "2026-03-21T10:31:00Z",
          "csi_2_4": {
            "file": "csi_baseline_2_4.csi",
            "file_size_mb": 125.4,
            "channel": 6,
            "frequency_mhz": 2437,
            "n_subcarriers": 114,
            "capture_duration_seconds": 30
          },
          "csi_5": {
            "file": "csi_baseline_5.csi",
            "file_size_mb": 128.1,
            "channel": 36,
            "frequency_mhz": 5180,
            "n_subcarriers": 242,
            "capture_duration_seconds": 30
          },
          "notes": "No obstruction between TX and RX"
        },
        ...
      ]
    }

Post-Processing Notes:
  - Use PicoScenes tools to convert .csi to HDF5 or Matlab format
  - Extract phase, magnitude, and correlation data from CSI frames
  - Apply frequency-domain analysis for attenuation characterization
  - Consider Fourier transforms for time-frequency representation

Author: Wi-Fi Sensing Research Team
Version: 1.0.0
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('csi_experiment_controller.log')
    ]
)
logger = logging.getLogger(__name__)


class CSIExperimentController:
    """Orchestrates multi-phase CSI measurement experiments."""

    # Channel to frequency mapping
    FREQ_2_4 = {
        1: 2412, 2: 2417, 3: 2422, 4: 2427, 5: 2432, 6: 2437, 7: 2442,
        8: 2447, 9: 2452, 10: 2457, 11: 2462, 12: 2467, 13: 2472
    }

    FREQ_5 = {
        36: 5180, 40: 5200, 44: 5220, 48: 5240, 52: 5260, 56: 5280, 60: 5300,
        64: 5320, 100: 5500, 104: 5520, 108: 5540, 112: 5560, 116: 5580,
        120: 5600, 124: 5620, 128: 5640, 132: 5660, 136: 5680, 140: 5700,
        144: 5720, 149: 5745, 153: 5765, 157: 5785, 161: 5805, 165: 5825,
        169: 5845, 173: 5865, 177: 5885
    }

    # Subcarrier counts for different bandwidths
    SUBCARRIERS = {
        '20': 114,  # 52 data + 4 pilot (2.4 GHz), 52 data + 4 pilot (5 GHz)
        '40': 242,  # 108 data + 4 pilot (5 GHz), 108 data + 4 pilot (2.4 GHz)
        '80': 514,  # 234 data + 4 pilot (5 GHz)
        '160': 1030  # 468 data + 4 pilot (5 GHz)
    }

    def __init__(
        self,
        experiment_id: str,
        materials: List[str],
        duration_per_band: int,
        interface: str,
        channel_2_4: int,
        channel_5: int,
        bandwidth: str = '20',
        output_dir: Optional[str] = None,
        location: str = 'unknown',
        distance_cm: Optional[float] = None,
        temperature_c: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        environment_id: str = 'unknown'
    ):
        """
        Initialize CSI experiment controller.

        Args:
            experiment_id: Unique identifier for this experiment
            materials: List of material names (first is baseline)
            duration_per_band: CSI capture duration per band in seconds
            interface: Wi-Fi interface name
            channel_2_4: 2.4 GHz channel (1-13)
            channel_5: 5 GHz channel (36, 40, 44, etc.)
            bandwidth: Bandwidth string ('20', '40', '80', '160')
            output_dir: Output directory for CSI files and metadata
            location: Physical location description
            distance_cm: Distance between TX and RX in cm
            temperature_c: Room temperature in Celsius
            humidity_percent: Room humidity in percent
            environment_id: Environment identifier
        """
        self.experiment_id = experiment_id
        self.materials = materials
        self.duration_per_band = duration_per_band
        self.interface = interface
        self.channel_2_4 = channel_2_4
        self.channel_5 = channel_5
        self.bandwidth = bandwidth
        self.location = location
        self.distance_cm = distance_cm
        self.temperature_c = temperature_c
        self.humidity_percent = humidity_percent
        self.environment_id = environment_id

        # Set output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(f"csi_experiment_{experiment_id}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Experiment state
        self.phases = []
        self.start_time = None
        self.end_time = None
        self._capture_process = None

    def _validate_hardware(self) -> bool:
        """
        Validate CSI hardware and PicoScenes installation.

        Returns:
            True if hardware is valid, False otherwise
        """
        logger.info("Validating CSI hardware...")

        # Check if interface exists
        try:
            result = subprocess.run(
                f"ip link show {self.interface}",
                shell=True,
                capture_output=True,
                timeout=3
            )
            if result.returncode != 0:
                logger.error(f"Interface {self.interface} not found")
                return False
        except Exception as e:
            logger.error(f"Interface check failed: {e}")
            return False

        # Check for PicoScenes
        try:
            result = subprocess.run(
                "which PicoScenes",
                shell=True,
                capture_output=True,
                timeout=3
            )
            if result.returncode != 0:
                logger.error(
                    "PicoScenes not found. "
                    "Install from https://github.com/Marsrocky/PicoScenes"
                )
                return False
        except Exception as e:
            logger.error(f"PicoScenes check failed: {e}")
            return False

        logger.info("Hardware validation passed")
        return True

    def setup_phases(self):
        """
        Define experiment phases.

        First phase is always "baseline" (air / no obstruction).
        Subsequent phases are material tests.
        """
        self.phases = []

        # Baseline phase
        self.phases.append({
            'phase_id': 0,
            'label': 'baseline',
            'material_class': 'air',
            'csi_2_4_file': f"csi_baseline_2_4_ch{self.channel_2_4}.csi",
            'csi_5_file': f"csi_baseline_5_ch{self.channel_5}.csi",
            'notes': 'No obstruction between TX and RX'
        })

        # Material phases
        for idx, material in enumerate(self.materials[1:], start=1):
            material_label = material.lower().replace(' ', '_')
            self.phases.append({
                'phase_id': idx,
                'label': f'material_{idx}',
                'material_class': material,
                'csi_2_4_file': f"csi_{material_label}_2_4_ch{self.channel_2_4}.csi",
                'csi_5_file': f"csi_{material_label}_5_ch{self.channel_5}.csi",
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
            prompt = f"\n{'='*60}\nCSI Phase: {phase_label} ({material})\nRemove all obstructions between TX and RX.\nPress ENTER when ready (or 'q' to quit): "
        else:
            prompt = f"\n{'='*60}\nCSI Phase: {phase_label} ({material})\nPlace {material} between TX and RX.\nPress ENTER when ready (or 'q' to quit): "

        response = input(prompt).strip().lower()
        return response != 'q'

    def capture_csi_band(
        self,
        channel: int,
        band: str,
        output_file: str
    ) -> bool:
        """
        Capture CSI data at a specific channel and band.

        Args:
            channel: IEEE channel number
            band: '2.4' or '5' (GHz)
            output_file: Output .csi file path

        Returns:
            True if capture succeeded, False otherwise
        """
        logger.info(f"Capturing CSI at {band} GHz channel {channel}")
        logger.info(f"Duration: {self.duration_per_band}s, Output: {output_file}")

        # Build capture script path
        capture_script = Path(__file__).parent / 'picoscenes_capture.sh'

        if not capture_script.exists():
            logger.error(f"Capture script not found: {capture_script}")
            return False

        # Build command
        cmd = [
            'bash', str(capture_script),
            '--interface', self.interface,
            '--channel', str(channel),
            '--bandwidth', self.bandwidth,
            '--duration', str(self.duration_per_band),
            '--output-dir', str(self.output_dir)
        ]

        logger.info(f"Running: {' '.join(cmd)}")

        try:
            # Launch capture process
            self._capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Monitor process
            start_time = time.time()
            while True:
                returncode = self._capture_process.poll()

                if returncode is not None:
                    # Process finished
                    stdout, stderr = self._capture_process.communicate()
                    if returncode == 0:
                        logger.info(f"CSI capture completed for {band} GHz channel {channel}")
                        return True
                    else:
                        logger.error(
                            f"Capture failed with code {returncode}\n"
                            f"stdout: {stdout}\nstderr: {stderr}"
                        )
                        return False

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > self.duration_per_band + 30:
                    logger.warning("Capture timeout exceeded. Terminating.")
                    self._capture_process.terminate()
                    self._capture_process.wait()
                    return False

                time.sleep(1)

        except KeyboardInterrupt:
            logger.warning("Capture interrupted by user")
            if self._capture_process:
                self._capture_process.terminate()
                self._capture_process.wait()
            return False
        except Exception as e:
            logger.error(f"Error during capture: {e}", exc_info=True)
            if self._capture_process:
                self._capture_process.terminate()
            return False

    def run_phase(self, phase: Dict) -> bool:
        """
        Execute a single CSI measurement phase (dual-band capture).

        Args:
            phase: Phase dictionary

        Returns:
            True if phase completed successfully, False otherwise
        """
        phase_label = phase['label']
        material_class = phase['material_class']

        logger.info(f"Starting CSI phase: {phase_label} ({material_class})")

        phase['start_time'] = datetime.utcnow().isoformat() + 'Z'

        # Capture 2.4 GHz
        csi_2_4_path = self.output_dir / phase['csi_2_4_file']
        if not self.capture_csi_band(self.channel_2_4, '2.4', str(csi_2_4_path)):
            logger.error(f"2.4 GHz capture failed for {phase_label}")
            return False

        # Record 2.4 GHz metadata
        if csi_2_4_path.exists():
            file_size_mb = csi_2_4_path.stat().st_size / 1024 / 1024
            phase['csi_2_4'] = {
                'file': phase['csi_2_4_file'],
                'file_size_mb': round(file_size_mb, 2),
                'channel': self.channel_2_4,
                'frequency_mhz': self.FREQ_2_4.get(self.channel_2_4),
                'n_subcarriers': self.SUBCARRIERS.get(self.bandwidth, 114),
                'capture_duration_seconds': self.duration_per_band
            }

        # Pause between captures
        logger.info("Pausing 5 seconds before 5 GHz capture...")
        time.sleep(5)

        # Capture 5 GHz
        csi_5_path = self.output_dir / phase['csi_5_file']
        if not self.capture_csi_band(self.channel_5, '5', str(csi_5_path)):
            logger.error(f"5 GHz capture failed for {phase_label}")
            return False

        # Record 5 GHz metadata
        if csi_5_path.exists():
            file_size_mb = csi_5_path.stat().st_size / 1024 / 1024
            phase['csi_5'] = {
                'file': phase['csi_5_file'],
                'file_size_mb': round(file_size_mb, 2),
                'channel': self.channel_5,
                'frequency_mhz': self.FREQ_5.get(self.channel_5),
                'n_subcarriers': self.SUBCARRIERS.get(self.bandwidth, 242),
                'capture_duration_seconds': self.duration_per_band
            }

        phase['end_time'] = datetime.utcnow().isoformat() + 'Z'
        logger.info(f"Phase completed: {phase_label}")
        return True

    def run_experiment(self, start_phase: int = 0) -> bool:
        """
        Execute the full CSI experiment.

        Args:
            start_phase: Phase index to start from (0 = baseline)

        Returns:
            True if experiment completed, False if aborted
        """
        if start_phase >= len(self.phases):
            logger.error(f"Invalid start phase: {start_phase}")
            return False

        # Validate hardware
        if not self._validate_hardware():
            logger.error("Hardware validation failed")
            return False

        self.start_time = datetime.utcnow().isoformat() + 'Z'
        logger.info(f"CSI Experiment started: {self.start_time}")

        # Run phases
        for phase_idx in range(start_phase, len(self.phases)):
            phase = self.phases[phase_idx]

            # Prompt user
            if not self.prompt_for_phase(phase):
                logger.info("Experiment canceled by user")
                return False

            # Run phase
            if not self.run_phase(phase):
                logger.error(f"Phase failed: {phase['label']}")
                return False

            # Pause between phases
            if phase_idx < len(self.phases) - 1:
                logger.info("Waiting 10s before next phase...")
                time.sleep(10)

        self.end_time = datetime.utcnow().isoformat() + 'Z'
        logger.info(f"CSI Experiment completed: {self.end_time}")
        return True

    def save_manifest(self):
        """Save experiment metadata and CSI file references to JSON manifest."""
        manifest = {
            'experiment_id': self.experiment_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'location': self.location,
            'distance_cm': self.distance_cm,
            'temperature_c': self.temperature_c,
            'humidity_percent': self.humidity_percent,
            'interface': self.interface,
            'bandwidth': f"{self.bandwidth} MHz",
            'channel_2_4': self.channel_2_4,
            'channel_5': self.channel_5,
            'frequency_2_4_mhz': self.FREQ_2_4.get(self.channel_2_4),
            'frequency_5_mhz': self.FREQ_5.get(self.channel_5),
            'environment_id': self.environment_id,
            'phases': self.phases
        }

        # Calculate total duration
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
            manifest['duration_seconds'] = int((end - start).total_seconds())

        manifest_file = self.output_dir / f"{self.experiment_id}_csi_manifest.json"

        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest saved: {manifest_file}")

    def summary(self):
        """Print experiment summary."""
        total_csi_size = 0
        completed_phases = 0

        for phase in self.phases:
            if phase.get('csi_2_4') and phase['csi_2_4'].get('file_size_mb'):
                total_csi_size += phase['csi_2_4']['file_size_mb']
            if phase.get('csi_5') and phase['csi_5'].get('file_size_mb'):
                total_csi_size += phase['csi_5']['file_size_mb']
            if phase.get('end_time'):
                completed_phases += 1

        print("\n" + "="*70)
        print("CSI EXPERIMENT SUMMARY")
        print("="*70)
        print(f"Experiment ID: {self.experiment_id}")
        print(f"Output Directory: {self.output_dir}")
        print(f"Start Time: {self.start_time}")
        print(f"End Time: {self.end_time}")
        print(f"Location: {self.location}")
        print(f"Distance: {self.distance_cm} cm")
        print(f"Interface: {self.interface}")
        print(f"Bandwidth: {self.bandwidth} MHz")
        print(f"2.4 GHz: Channel {self.channel_2_4}")
        print(f"5 GHz: Channel {self.channel_5}")
        print(f"Phases Completed: {completed_phases}/{len(self.phases)}")
        print(f"Total CSI Data: {total_csi_size:.2f} MB")
        print("\nPhases:")
        for phase in self.phases:
            status = "✓" if phase.get('end_time') else "✗"
            has_2_4 = "✓" if phase.get('csi_2_4') else "✗"
            has_5 = "✓" if phase.get('csi_5') else "✗"
            print(f"  {status} {phase['label']:20} (2.4G: {has_2_4}, 5G: {has_5})")
        print("="*70 + "\n")


def main():
    """Parse arguments and run CSI experiment."""
    parser = argparse.ArgumentParser(
        description='Orchestrate dual-band CSI experiments with PicoScenes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Baseline CSI experiment with 30s per band
  python3 csi_experiment_controller.py \\
    --experiment-id csi_001 \\
    --materials "baseline,wood,concrete" \\
    --duration-per-band 30 \\
    --interface wlan0 \\
    --channel-2-4 6 \\
    --channel-5 36 \\
    --location "Lab A" \\
    --distance-cm 50

  # Resume from phase 2
  python3 csi_experiment_controller.py \\
    --experiment-id csi_001 \\
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
        default=['baseline'],
        help='Comma-separated list of materials'
    )
    parser.add_argument(
        '--duration-per-band', '-d',
        type=int,
        default=30,
        help='CSI capture duration per band in seconds (default: 30)'
    )
    parser.add_argument(
        '--interface', '-i',
        required=True,
        help='Wi-Fi interface name (e.g., wlan0)'
    )
    parser.add_argument(
        '--channel-2-4',
        type=int,
        required=True,
        help='2.4 GHz channel (1-13)'
    )
    parser.add_argument(
        '--channel-5',
        type=int,
        required=True,
        help='5 GHz channel (e.g., 36, 40, 44, etc.)'
    )
    parser.add_argument(
        '--bandwidth', '-b',
        choices=['20', '40', '80', '160'],
        default='20',
        help='Bandwidth in MHz (default: 20)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for CSI files'
    )
    parser.add_argument(
        '--location',
        default='unknown',
        help='Physical location description'
    )
    parser.add_argument(
        '--distance-cm',
        type=float,
        help='Distance between TX and RX in cm'
    )
    parser.add_argument(
        '--temperature-c',
        type=float,
        help='Room temperature in Celsius'
    )
    parser.add_argument(
        '--humidity-percent',
        type=float,
        help='Room humidity percent'
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
        help='Resume from this phase index'
    )

    args = parser.parse_args()

    # Create controller
    controller = CSIExperimentController(
        experiment_id=args.experiment_id,
        materials=args.materials,
        duration_per_band=args.duration_per_band,
        interface=args.interface,
        channel_2_4=args.channel_2_4,
        channel_5=args.channel_5,
        bandwidth=args.bandwidth,
        output_dir=args.output_dir,
        location=args.location,
        distance_cm=args.distance_cm,
        temperature_c=args.temperature_c,
        humidity_percent=args.humidity_percent,
        environment_id=args.environment_id
    )

    # Setup and run
    controller.setup_phases()

    if controller.run_experiment(start_phase=args.resume_phase):
        controller.save_manifest()
        controller.summary()
        logger.info("CSI Experiment completed successfully")
    else:
        logger.warning("CSI Experiment did not complete")
        controller.save_manifest()
        sys.exit(1)


if __name__ == '__main__':
    main()
