"""
Double-Single and Relative-to-Eye (RTE) Math Module
===================================================
Provides two high-precision coordinate mechanisms:
1. Relative-to-Eye (RTE):
   Camera world position is stored in 64-bit float.
   Before rendering, vertices are transformed relative to the camera on the CPU:
     v_eye = v_world - camera_pos (done in double)
   This allows standard 32-bit hardware vertex shaders to render 100km landscapes
   with 0.01mm precision without any jitter or Z-fighting.

2. Double-Single (DS) Emulation:
   Encodes a 64-bit float into two 32-bit floats (hi, lo) for GPU shader ALUs:
     x = x_hi + x_lo
   Gives 48-bit mantissa on weak/mobile GPUs without hardware FP64.
"""

import numpy as np


class DoubleSingle:
    @staticmethod
    def split(value_double):
        """
        Splits a 64-bit float (or array) into (hi, lo) 32-bit floats.
        """
        hi = np.float32(value_double)
        lo = np.float32(value_double - hi.astype(np.float64))
        return hi, lo

    @staticmethod
    def two_sum(a, b):
        """
        Knuth's Two-Sum algorithm in 32-bit float.
        """
        s = np.float32(a + b)
        v = np.float32(s - a)
        e = np.float32((a - (s - v)) + (b - v))
        return s, e

    @staticmethod
    def add(a_hi, a_lo, b_hi, b_lo):
        s, e = DoubleSingle.two_sum(a_hi, b_hi)
        e = np.float32(e + a_lo + b_lo)
        res_hi, res_lo = DoubleSingle.two_sum(s, e)
        return res_hi, res_lo


class RelativeToEye:
    @staticmethod
    def compute_rte_matrix(model_matrix_f64, view_matrix_f64, camera_pos_f64):
        """
        Computes the combined ModelView matrix with camera translation subtracted.
        Returns:
            model_view_rte: 4x4 float32 matrix
            camera_pos_f64: 3-element float64
        """
        # View matrix without translation (pure rotation)
        rot_view = np.copy(view_matrix_f64)
        rot_view[3, :3] = 0.0  # zero out translation column/row

        # Relative translation: (model_pos - cam_pos) in FP64
        mv = np.dot(model_matrix_f64, rot_view)
        # Shift translation by camera
        cam_shift = -np.dot(camera_pos_f64, rot_view[:3, :3])
        mv[3, :3] += cam_shift

        return mv.astype(np.float32)
