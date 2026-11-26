"""Teacher camera recording (training labels only — never used at inference).

* ``OrbbecDepth``: Orbbec Femto Bolt (or any Orbbec camera) via ``pyorbbecsdk``.
  Records depth in mm. 3D body joints are produced offline from the recorded
  session with the Azure Kinect Body Tracking SDK (Orbbec ships a K4A wrapper)
  and saved as ``keypoints.npz``; map joint names with
  ``wispec.room.pointing.K4ABT_TO_WISPEC``.
* ``OpenCVCamera``: any webcam, RGB (fallback teacher, like the WiFiCam demo).

Frames are stamped with host ``time.time_ns()`` — the same clock PicoScenes
uses on this machine — and written in chunks to keep memory bounded.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np


class TeacherRecorder:
    def __init__(self, out_dir: Path, store_size: int = 256, fps: float = 15.0):
        self.out_dir, self.store_size, self.fps = Path(out_dir), store_size, fps
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t: list[int] = []
        self._f: list[np.ndarray] = []

    # subclasses implement
    def open(self): ...
    def read(self) -> np.ndarray | None: ...
    def close(self): ...

    def _resize(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        s = self.store_size
        side = min(h, w)                       # centre crop to square, then nearest resize
        y0, x0 = (h - side) // 2, (w - side) // 2
        img = img[y0:y0 + side, x0:x0 + side]
        ys = (np.arange(s) * side / s).astype(int)
        xs = (np.arange(s) * side / s).astype(int)
        return img[ys][:, xs]

    def _loop(self):
        period = 1.0 / self.fps
        nxt = time.monotonic()
        while not self._stop.is_set():
            img = self.read()
            if img is not None:
                self._t.append(time.time_ns())
                self._f.append(self._resize(img))
            nxt += period
            time.sleep(max(0.0, nxt - time.monotonic()))

    def start(self):
        self.open()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> Path:
        self._stop.set()
        if self._thread:
            self._thread.join()
        self.close()
        out = self.out_dir / "teacher.npz"
        np.savez_compressed(out, t_ns=np.asarray(self._t, np.int64), frames=np.stack(self._f))
        return out


class OrbbecDepth(TeacherRecorder):
    def open(self):
        from pyorbbecsdk import Config, OBSensorType, Pipeline  # type: ignore
        self._pipe = Pipeline()
        cfg = Config()
        profiles = self._pipe.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
        cfg.enable_stream(profiles.get_default_video_stream_profile())
        self._pipe.start(cfg)

    def read(self):
        frames = self._pipe.wait_for_frames(100)
        d = frames.get_depth_frame() if frames else None
        if d is None:
            return None
        arr = np.frombuffer(d.get_data(), dtype=np.uint16).reshape(d.get_height(), d.get_width())
        return (arr.astype(np.float32) * d.get_depth_scale()).astype(np.uint16)   # -> mm

    def close(self):
        self._pipe.stop()


class OpenCVCamera(TeacherRecorder):
    def __init__(self, out_dir: Path, device: int = 0, **kw):
        super().__init__(out_dir, **kw)
        self.device = device

    def open(self):
        import cv2  # type: ignore
        self._cv2 = cv2
        self._cap = cv2.VideoCapture(self.device)

    def read(self):
        ok, img = self._cap.read()
        return self._cv2.cvtColor(img, self._cv2.COLOR_BGR2RGB) if ok else None

    def close(self):
        self._cap.release()


def make_teacher(kind: str, out_dir: Path, **kw) -> TeacherRecorder:
    return {"orbbec": OrbbecDepth, "opencv": OpenCVCamera}[kind](out_dir, **kw)
