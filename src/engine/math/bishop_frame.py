"""
Bishop Frame (Rotation-Minimizing Frame / RMF) Module
=====================================================
Computes a continuous, twist-free orthonormal coordinate frame (T, N, B)
along an arbitrary 3D parametric curve C(v).

Unlike the classic Frenet-Serret frame:
- Works seamlessly on straight lines (where curvature kappa = 0).
- Has zero torsion singularities on inflection points.
- Guarantees minimum rotation of cross-section profiles along architectural paths.
"""

import numpy as np


class BishopFrame:
    @staticmethod
    def compute(curve_points, is_closed=False):
        """
        curve_points: (N, 3) numpy array
        returns:
            tangents: (N, 3)
            normals: (N, 3)
            binormals: (N, 3)
        """
        n = len(curve_points)
        if n < 2:
            raise ValueError("Curve must have at least 2 points")

        tangents = np.zeros_like(curve_points)
        normals = np.zeros_like(curve_points)
        binormals = np.zeros_like(curve_points)

        # 1. Compute tangents
        for i in range(n):
            if is_closed:
                ip = (i + 1) % n
                im = (i - 1) % n
                t_vec = curve_points[ip] - curve_points[im]
            else:
                if i == 0:
                    t_vec = curve_points[1] - curve_points[0]
                elif i == n - 1:
                    t_vec = curve_points[-1] - curve_points[-2]
                else:
                    t_vec = curve_points[i + 1] - curve_points[i - 1]

            norm = np.linalg.norm(t_vec)
            tangents[i] = t_vec / (norm if norm > 1e-9 else 1.0)

        # 2. Initial normal orthogonal to tangent[0]
        t0 = tangents[0]
        arbitrary = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        if abs(np.dot(t0, arbitrary)) > 0.9:
            arbitrary = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        n0 = np.cross(t0, arbitrary)
        n0 /= np.linalg.norm(n0)
        b0 = np.cross(t0, n0)

        normals[0] = n0
        binormals[0] = b0

        # 3. Double-reflection method (Wang et al. 2008) for ultra-accurate parallel transport
        for i in range(n - 1):
            p_i = curve_points[i]
            p_next = curve_points[i + 1]
            t_i = tangents[i]
            t_next = tangents[i + 1]
            n_i = normals[i]

            v1 = p_next - p_i
            c1 = np.dot(v1, v1)

            if c1 < 1e-12:
                normals[i + 1] = n_i
                binormals[i + 1] = binormals[i]
                continue

            r_l = n_i - (2.0 / c1) * np.dot(v1, n_i) * v1
            t_l = t_i - (2.0 / c1) * np.dot(v1, t_i) * v1

            v2 = t_next - t_l
            c2 = np.dot(v2, v2)

            if c2 < 1e-12:
                n_next = r_l
            else:
                n_next = r_l - (2.0 / c2) * np.dot(v2, r_l) * v2

            n_next /= np.linalg.norm(n_next)
            b_next = np.cross(t_next, n_next)
            b_next /= np.linalg.norm(b_next)

            normals[i + 1] = n_next
            binormals[i + 1] = b_next

        return tangents, normals, binormals
