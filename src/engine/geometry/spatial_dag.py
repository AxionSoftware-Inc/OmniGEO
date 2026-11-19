"""
Spatial DAG & Symmetry Engine Module
====================================
Implements a Directed Acyclic Graph (DAG) for high-performance BIM/CAD scenes:
- Canonical prototype dictionary (unique meshes stored once in VRAM).
- Hierarchy nodes: Campus -> Building -> Floor -> Room -> Component.
- Flattened $SE(3)$ transformation buffer for zero-overhead GPU instancing.
"""

import numpy as np


class MeshPrototype:
    def __init__(self, name, vertices, indices, normals=None):
        self.name = name
        self.vertices = np.array(vertices, dtype=np.float32)
        self.indices = np.array(indices, dtype=np.uint32)
        self.normals = normals if normals is not None else np.zeros_like(self.vertices)
        self.num_vertices = len(self.vertices)
        self.num_triangles = len(self.indices) // 3
        self.vram_bytes = self.vertices.nbytes + self.indices.nbytes + self.normals.nbytes


class SpatialDAG:
    def __init__(self):
        self.prototypes = {}          # name -> MeshPrototype
        self.instances = {}           # name -> list of 4x4 affine transform matrices
        self.cached_instance_buffers = {}

    def register_prototype(self, prototype: MeshPrototype):
        self.prototypes[prototype.name] = prototype
        if prototype.name not in self.instances:
            self.instances[prototype.name] = []

    def add_instance(self, prototype_name, transform_matrix_4x4):
        if prototype_name not in self.prototypes:
            raise KeyError(f"Prototype '{prototype_name}' not registered")
        self.instances[prototype_name].append(transform_matrix_4x4)

    def finalize_buffers(self):
        """
        Compacts all instance matrices into contiguous float32 buffers for GPU upload.
        """
        for name, matrix_list in self.instances.items():
            if len(matrix_list) > 0:
                self.cached_instance_buffers[name] = np.array(matrix_list, dtype=np.float32)
            else:
                self.cached_instance_buffers[name] = np.zeros((0, 4, 4), dtype=np.float32)

    def get_statistics(self):
        total_unique_verts = sum(p.num_vertices for p in self.prototypes.values())
        total_unique_tris = sum(p.num_triangles for p in self.prototypes.values())
        total_unique_mesh_bytes = sum(p.vram_bytes for p in self.prototypes.values())

        total_instances = sum(len(mats) for mats in self.instances.values())
        total_matrix_bytes = total_instances * 64  # 4x4 float32 = 64 bytes

        uncompressed_raw_verts = sum(self.prototypes[name].num_vertices * len(mats) for name, mats in self.instances.items())
        uncompressed_raw_tris = sum(self.prototypes[name].num_triangles * len(mats) for name, mats in self.instances.items())
        uncompressed_raw_bytes = sum(self.prototypes[name].vram_bytes * len(mats) for name, mats in self.instances.items())

        dag_total_bytes = total_unique_mesh_bytes + total_matrix_bytes
        compression_ratio = (uncompressed_raw_bytes / dag_total_bytes) if dag_total_bytes > 0 else 1.0

        return {
            "unique_prototypes": len(self.prototypes),
            "total_instances": total_instances,
            "unique_mesh_vram_kb": total_unique_mesh_bytes / 1024.0,
            "matrix_buffer_vram_kb": total_matrix_bytes / 1024.0,
            "total_dag_vram_kb": dag_total_bytes / 1024.0,
            "total_dag_vram_mb": dag_total_bytes / (1024.0 * 1024.0),
            "uncompressed_raw_vram_mb": uncompressed_raw_bytes / (1024.0 * 1024.0),
            "uncompressed_triangles": uncompressed_raw_tris,
            "compression_ratio": compression_ratio
        }
