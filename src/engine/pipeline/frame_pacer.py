"""
High-Precision Frame Pacer & Uncapped Rate Controller
======================================================
Provides sub-microsecond frame pacing for high refresh monitors (144Hz, 240Hz, 360Hz, 720Hz+)
and completely uncapped hardware rendering throughput.

Features:
- Native Rust DLL backend (`rust_core.dll`) with sub-microsecond hybrid spin-wait.
- Pure Python high-precision fallback (`time.perf_counter_ns()`).
- Target FPS modes: 30, 60, 120, 144, 240, 360, 720, or Uncapped (0).
"""

import time
import os
import ctypes
from typing import Optional

class NativeRustPacer:
    """Wrapper around rust_core.dll C-ABI exports."""
    def __init__(self, dll_path: str, target_fps: int = 0):
        self.dll = ctypes.CDLL(dll_path)
        self.dll.omni_pacer_create.restype = ctypes.c_void_p
        self.dll.omni_pacer_create.argtypes = [ctypes.c_uint32]
        self.dll.omni_pacer_set_limit.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.dll.omni_pacer_begin_frame.restype = ctypes.c_double
        self.dll.omni_pacer_begin_frame.argtypes = [ctypes.c_void_p]
        self.dll.omni_pacer_get_fps.restype = ctypes.c_double
        self.dll.omni_pacer_get_fps.argtypes = [ctypes.c_void_p]
        self.dll.omni_pacer_destroy.argtypes = [ctypes.c_void_p]

        self.handle = self.dll.omni_pacer_create(target_fps)

    def set_limit(self, target_fps: int):
        self.dll.omni_pacer_set_limit(self.handle, target_fps)

    def begin_frame(self) -> float:
        """Blocks to maintain target FPS, or returns immediately if uncapped. Returns frame time in microseconds."""
        return self.dll.omni_pacer_begin_frame(self.handle)

    def current_fps(self) -> float:
        return self.dll.omni_pacer_get_fps(self.handle)

    def __del__(self):
        if hasattr(self, 'handle') and self.handle:
            self.dll.omni_pacer_destroy(self.handle)
            self.handle = None


class PythonHighResPacer:
    """High-resolution pure Python frame pacer using time.perf_counter_ns()."""
    def __init__(self, target_fps: int = 0):
        self.target_fps = target_fps
        self.target_ns = 0 if target_fps <= 0 else int(1_000_000_000 / target_fps)
        self.last_frame_ns = time.perf_counter_ns()
        self.frame_count = 0
        self.sample_start_ns = self.last_frame_ns
        self.current_fps_val = 0.0
        self.last_frame_time_us = 0.0

    def set_limit(self, target_fps: int):
        self.target_fps = target_fps
        self.target_ns = 0 if target_fps <= 0 else int(1_000_000_000 / target_fps)

    def begin_frame(self) -> float:
        now = time.perf_counter_ns()
        if self.target_ns > 0:
            elapsed = now - self.last_frame_ns
            if elapsed < self.target_ns:
                remaining_ns = self.target_ns - elapsed
                # Hybrid sleep + spin
                if remaining_ns > 2_000_000:
                    time.sleep((remaining_ns - 1_000_000) / 1_000_000_000.0)
                while (time.perf_counter_ns() - self.last_frame_ns) < self.target_ns:
                    pass

        now = time.perf_counter_ns()
        delta_ns = now - self.last_frame_ns
        self.last_frame_ns = now
        self.last_frame_time_us = delta_ns / 1_000.0

        self.frame_count += 1
        sample_elapsed = now - self.sample_start_ns
        if sample_elapsed >= 250_000_000: # 250ms
            self.current_fps_val = (self.frame_count * 1_000_000_000.0) / sample_elapsed
            self.frame_count = 0
            self.sample_start_ns = now

        return self.last_frame_time_us

    def current_fps(self) -> float:
        return self.current_fps_val


def create_frame_pacer(target_fps: int = 0):
    dll_rel = os.path.join(os.path.dirname(__file__), "..", "..", "..", "rust_core", "target", "release", "rust_core.dll")
    dll_path = os.path.abspath(dll_rel)
    if os.path.exists(dll_path):
        return NativeRustPacer(dll_path, target_fps)
    return PythonHighResPacer(target_fps)
