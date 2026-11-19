"""
OmniGeo Binary Format Specification (.omni)
============================================
High-performance zero-copy binary container for CAD/BIM spatial DAG models.

File Structure:
[Header: 64 bytes]
- Magic: 'OMNI' (4 bytes)
- Version: uint32 (4 bytes)
- Flags: uint32 (4 bytes)
- Bounding Box: 6 x float32 (24 bytes)
- Prototype Count: uint32 (4 bytes)
- Total Instances: uint32 (4 bytes)
- Material Count: uint32 (4 bytes)
- Reserved: 16 bytes

[Section 1: Materials (PBR)]
- Array of Material structs: baseColor(4f), roughness(f), metallic(f), reflectance(f), ao(f)

[Section 2: Canonical Prototypes]
- For each prototype:
  - Name: 32 bytes ASCII
  - Vertex Count: uint32
  - Triangle Count: uint32
  - Positions: (V * 3) float32 (or 16-bit quantized)
  - Normals: (V * 3) float32
  - Barycentric Flags: (V * 3) float32
  - Indices: (T * 3) uint32

[Section 3: Instances ($SE(3)$ Transformations)]
- For each prototype:
  - Instance count: uint32
  - Array of 4x4 float32 transformation matrices (count * 64 bytes)
"""

import struct
import zlib
import numpy as np


class OmniBinaryWriter:
    MAGIC = b'OMNI'
    VERSION = 1

    @staticmethod
    def write(filepath, prototypes, instances_dict, materials, bbox_min=(-100,-100,-100), bbox_max=(100,100,100)):
        """
        prototypes: dict of {name: {'vertices': np.array, 'normals': np.array, 'indices': np.array, 'bary': np.array}}
        instances_dict: dict of {name: list of 4x4 np.ndarray}
        materials: list of PBRMaterial dicts
        """
        proto_names = list(prototypes.keys())
        proto_count = len(proto_names)
        total_instances = sum(len(instances_dict.get(n, [])) for n in proto_names)
        mat_count = len(materials)

        with open(filepath, 'wb') as f:
            # 1. Header (64 bytes exact)
            header = struct.pack(
                '<4sII6fIII16s',
                OmniBinaryWriter.MAGIC,
                OmniBinaryWriter.VERSION,
                0, # Flags (0 = uncompressed, 1 = zlib)
                bbox_min[0], bbox_min[1], bbox_min[2],
                bbox_max[0], bbox_max[1], bbox_max[2],
                proto_count,
                total_instances,
                mat_count,
                b'\x00' * 16 # Reserved
            )
            f.write(header)

            # 2. Materials
            for mat in materials:
                # 32 bytes per material (8 floats)
                m_bytes = struct.pack(
                    '<8f',
                    mat['base_color'][0], mat['base_color'][1], mat['base_color'][2], mat['base_color'][3],
                    mat['roughness'], mat['metallic'], mat['reflectance'], mat['ao']
                )
                f.write(m_bytes)

            # 3. Canonical Prototypes
            for name in proto_names:
                proto = prototypes[name]
                verts = proto['vertices'].astype(np.float32)
                norms = proto['normals'].astype(np.float32)
                indices = proto['indices'].astype(np.uint32)
                barys = proto.get('bary', np.zeros_like(verts)).astype(np.float32)

                name_encoded = name.encode('utf-8')[:31].ljust(32, b'\x00')
                v_count = len(verts)
                t_count = len(indices) // 3

                proto_header = struct.pack('<32sII', name_encoded, v_count, t_count)
                f.write(proto_header)

                f.write(verts.tobytes())
                f.write(norms.tobytes())
                f.write(barys.tobytes())
                f.write(indices.tobytes())

            # 4. Instances Table
            for name in proto_names:
                mats = instances_dict.get(name, [])
                f.write(struct.pack('<I', len(mats)))
                if len(mats) > 0:
                    arr = np.array(mats, dtype=np.float32)
                    f.write(arr.tobytes())

        return True


class OmniBinaryReader:
    @staticmethod
    def read(filepath):
        """
        Fast zero-copy / buffer-based parser for .omni files.
        """
        with open(filepath, 'rb') as f:
            header_bytes = f.read(64)
            if len(header_bytes) < 64:
                raise ValueError("Corrupt .omni header")

            (magic, version, flags,
             b_min_x, b_min_y, b_min_z, b_max_x, b_max_y, b_max_z,
             proto_count, total_instances, mat_count, _) = struct.unpack('<4sII6fIII16s', header_bytes)

            if magic != OmniBinaryWriter.MAGIC:
                raise ValueError(f"Invalid magic identifier: {magic}")

            # Read Materials
            materials = []
            for _ in range(mat_count):
                m_data = struct.unpack('<8f', f.read(32))
                materials.append({
                    'base_color': m_data[0:4],
                    'roughness': m_data[4],
                    'metallic': m_data[5],
                    'reflectance': m_data[6],
                    'ao': m_data[7]
                })

            # Read Prototypes
            prototypes = {}
            for _ in range(proto_count):
                proto_header = f.read(40)
                name_bytes, v_count, t_count = struct.unpack('<32sII', proto_header)
                name = name_bytes.decode('utf-8').rstrip('\x00')

                verts = np.frombuffer(f.read(v_count * 3 * 4), dtype=np.float32).reshape(-1, 3)
                norms = np.frombuffer(f.read(v_count * 3 * 4), dtype=np.float32).reshape(-1, 3)
                barys = np.frombuffer(f.read(v_count * 3 * 4), dtype=np.float32).reshape(-1, 3)
                indices = np.frombuffer(f.read(t_count * 3 * 4), dtype=np.uint32)

                prototypes[name] = {
                    'vertices': verts,
                    'normals': norms,
                    'bary': barys,
                    'indices': indices
                }

            # Read Instances
            instances = {}
            for name in prototypes.keys():
                inst_count = struct.unpack('<I', f.read(4))[0]
                if inst_count > 0:
                    inst_bytes = f.read(inst_count * 16 * 4)
                    instances[name] = np.frombuffer(inst_bytes, dtype=np.float32).reshape(-1, 4, 4)
                else:
                    instances[name] = np.zeros((0, 4, 4), dtype=np.float32)

            return {
                'version': version,
                'bbox': ([b_min_x, b_min_y, b_min_z], [b_max_x, b_max_y, b_max_z]),
                'materials': materials,
                'prototypes': prototypes,
                'instances': instances,
                'total_instances': total_instances
            }
