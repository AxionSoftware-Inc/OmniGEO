"""
Physical Material Palette Module
=================================
Defines physically accurate measured architectural materials for BIM/CAD rendering.
Packed according to std430 alignment for zero-overhead GPU SSBO streaming:
Each material takes 32 bytes:
  vec4 baseColor (16B)
  float roughness (4B)
  float metallic (4B)
  float reflectance (4B)
  float ao (4B)
"""

import numpy as np


class PBRMaterial:
    def __init__(self, name, base_color, roughness, metallic, reflectance=0.5, ao=1.0):
        self.name = name
        self.base_color = base_color      # [r, g, b, a]
        self.roughness = roughness        # 0.04 (glossy) to 1.0 (rough)
        self.metallic = metallic          # 0.0 (dielectric) to 1.0 (conductor)
        self.reflectance = reflectance    # standard dielectric F0 = 0.5 (~4%)
        self.ao = ao


ARCHITECTURAL_PALETTE = {
    # 0: Polished Carrara Marble
    "marble_carrara": PBRMaterial("Carrara White Marble", [0.93, 0.93, 0.95, 1.0], roughness=0.12, metallic=0.0, reflectance=0.5),
    # 1: Architectural Patina Copper
    "architectural_copper": PBRMaterial("Copper Facade", [0.95, 0.64, 0.54, 1.0], roughness=0.25, metallic=1.0, reflectance=1.0),
    # 2: Brushed Structural Steel
    "structural_steel": PBRMaterial("Brushed Steel", [0.77, 0.78, 0.80, 1.0], roughness=0.35, metallic=0.95, reflectance=1.0),
    # 3: Anodized Black Aluminum
    "anodized_aluminum": PBRMaterial("Anodized Aluminum", [0.18, 0.19, 0.22, 1.0], roughness=0.28, metallic=0.90, reflectance=1.0),
    # 4: Architectural Concrete
    "cast_concrete": PBRMaterial("Smooth Cast Concrete", [0.55, 0.56, 0.58, 1.0], roughness=0.75, metallic=0.0, reflectance=0.4),
    # 5: Tinted Low-E Solar Glass
    "facade_glass": PBRMaterial("Low-E Tinted Glass", [0.15, 0.35, 0.45, 0.85], roughness=0.04, metallic=0.1, reflectance=0.7),
    # 6: Natural Oak Hardwood
    "oak_hardwood": PBRMaterial("Natural Oak Wood", [0.65, 0.45, 0.28, 1.0], roughness=0.42, metallic=0.0, reflectance=0.4),
    # 7: Gold / Brass Detail (1mm bolts)
    "gold_brass": PBRMaterial("Polished Brass Detail", [1.00, 0.82, 0.35, 1.0], roughness=0.18, metallic=1.0, reflectance=1.0),
    # 8: White Drywall Partition
    "interior_drywall": PBRMaterial("Matte Drywall", [0.91, 0.91, 0.90, 1.0], roughness=0.88, metallic=0.0, reflectance=0.5),
    # 9: Dark Granite Pavers
    "granite_pavers": PBRMaterial("Dark Flamed Granite", [0.22, 0.23, 0.25, 1.0], roughness=0.68, metallic=0.0, reflectance=0.45),
}


def build_gpu_material_ssbo():
    """
    Packs materials into a contiguous numpy float32 buffer for GPU SSBO.
    """
    materials = list(ARCHITECTURAL_PALETTE.values())
    count = len(materials)
    buffer = np.zeros(count * 8, dtype=np.float32)

    for i, m in enumerate(materials):
        offset = i * 8
        buffer[offset:offset+4] = m.base_color
        buffer[offset+4] = m.roughness
        buffer[offset+5] = m.metallic
        buffer[offset+6] = m.reflectance
        buffer[offset+7] = m.ao

    return buffer, ARCHITECTURAL_PALETTE
