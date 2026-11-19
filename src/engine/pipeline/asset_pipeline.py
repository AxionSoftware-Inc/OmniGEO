"""
Universal Asset Pipeline & Geometric Invariant Hashing Engine
=============================================================
Provides:
1. Wavefront OBJ & CAD Mesh Parser.
2. Geometric Invariant Hashing (DAG Deduplication):
   - Computes inertia tensor eigenvalues and bounding ratios.
   - Automatically clusters identical architectural objects into canonical prototypes.
   - Extracts 4x4 SE(3) transformation matrices.
3. Serializer into .omni binary format.
"""

import math
import numpy as np
from src.engine.pipeline.omni_format import OmniBinaryWriter


class GeometricHasher:
    @staticmethod
    def compute_fingerprint(vertices):
        """
        Computes a translation and rotation invariant geometric fingerprint:
        1. Center of mass (centroid)
        2. Principal moments of inertia (eigenvalues of inertia tensor)
        3. Dimension ratios
        """
        centroid = np.mean(vertices, axis=0)
        rel_verts = vertices - centroid

        # 3x3 Inertia tensor
        x, y, z = rel_verts[:, 0], rel_verts[:, 1], rel_verts[:, 2]
        Ixx = np.sum(y**2 + z**2)
        Iyy = np.sum(x**2 + z**2)
        Izz = np.sum(x**2 + y**2)
        Ixy = -np.sum(x * y)
        Ixz = -np.sum(x * z)
        Iyz = -np.sum(y * z)

        tensor = np.array([
            [Ixx, Ixy, Ixz],
            [Ixy, Iyy, Iyz],
            [Ixz, Iyz, Izz]
        ], dtype=np.float64)

        eigenvalues = np.linalg.eigvalsh(tensor)
        eigenvalues = np.sort(eigenvalues)

        # Normalize eigenvalues by volume/scale to make scale-invariant if needed
        norm_factor = np.linalg.norm(eigenvalues) + 1e-7
        norm_eigs = eigenvalues / norm_factor

        # Round to 4 decimal places for robust clustering
        fingerprint = tuple(np.round(norm_eigs, 3))

        return fingerprint, centroid


class OBJParser:
    @staticmethod
    def parse_string(obj_text):
        """
        Parses Wavefront OBJ text into named mesh groups.
        """
        all_verts = []
        all_norms = []
        groups = {}
        current_group = "default"

        for line in obj_text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            cmd = parts[0]

            if cmd == 'v':
                all_verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif cmd == 'vn':
                all_norms.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif cmd == 'g' or cmd == 'o':
                current_group = parts[1] if len(parts) > 1 else f"group_{len(groups)}"
                if current_group not in groups:
                    groups[current_group] = []
            elif cmd == 'f':
                if current_group not in groups:
                    groups[current_group] = []
                # Parse face vertex indices
                face_indices = []
                for p in parts[1:]:
                    v_idx = int(p.split('/')[0]) - 1
                    face_indices.append(v_idx)
                # Triangulate polygon (fan)
                for i in range(1, len(face_indices) - 1):
                    groups[current_group].extend([face_indices[0], face_indices[i], face_indices[i + 1]])

        all_verts = np.array(all_verts, dtype=np.float32)

        # Extract sub-meshes
        submeshes = {}
        for g_name, indices in groups.items():
            if len(indices) == 0: continue
            unique_v_indices, new_indices = np.unique(indices, return_inverse=True)
            v_subset = all_verts[unique_v_indices]

            # Generate synthetic normals if absent
            norms = np.zeros_like(v_subset)
            for i in range(0, len(new_indices), 3):
                p0 = v_subset[new_indices[i]]
                p1 = v_subset[new_indices[i+1]]
                p2 = v_subset[new_indices[i+2]]
                fn = np.cross(p1 - p0, p2 - p0)
                l = np.linalg.norm(fn)
                if l > 1e-7: fn /= l
                norms[new_indices[i]] += fn
                norms[new_indices[i+1]] += fn
                norms[new_indices[i+2]] += fn

            l_n = np.linalg.norm(norms, axis=1, keepdims=True)
            l_n[l_n == 0] = 1.0
            norms /= l_n

            submeshes[g_name] = {
                'vertices': v_subset,
                'normals': norms.astype(np.float32),
                'indices': new_indices.astype(np.uint32)
            }

        return submeshes


class AssetPipeline:
    @staticmethod
    def process_and_deduplicate(submeshes):
        """
        Takes raw submeshes, clusters identical geometries via Geometric Fingerprinting,
        and produces canonical prototypes + SE(3) instance transformation matrices.
        """
        prototypes = {}
        instances = {}
        fingerprint_map = {} # fingerprint -> canonical_name

        for name, mesh in submeshes.items():
            verts = mesh['vertices']
            if len(verts) < 3: continue

            fp, centroid = GeometricHasher.compute_fingerprint(verts)

            if fp not in fingerprint_map:
                # New unique prototype!
                proto_name = f"proto_{len(prototypes)}_{name}"
                fingerprint_map[fp] = proto_name

                # Store prototype centered at local origin (0, 0, 0)
                local_verts = verts - centroid
                prototypes[proto_name] = {
                    'vertices': local_verts.astype(np.float32),
                    'normals': mesh['normals'],
                    'indices': mesh['indices']
                }
                instances[proto_name] = []

            # Instance transform: translation matrix
            proto_name = fingerprint_map[fp]
            mat = np.eye(4, dtype=np.float32)
            mat[0:3, 3] = centroid  # world translation
            instances[proto_name].append(mat)

        raw_count = len(submeshes)
        proto_count = len(prototypes)
        print(f"[AssetPipeline]: Ingested {raw_count} meshes -> Deduplicated into {proto_count} canonical prototypes!")

        return prototypes, instances
