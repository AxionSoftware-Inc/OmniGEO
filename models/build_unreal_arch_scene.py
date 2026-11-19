import bpy
import math
import os

print("=== STARTING UNREAL ARCHITECTURAL SCENE BUILDER ===")

# Clear existing scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Helper to create Principled PBR material
texture_dir = os.path.abspath(r"d:\Geometry soft\models\textures")

def create_pbr_mat(name, color=(0.8, 0.8, 0.8, 1.0), metallic=0.0, roughness=0.5, tex_filename=None, transmission=0.0, normal_filename=None):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # Settings for Blender 4+/5+ Principled BSDF
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if 'Transmission Weight' in bsdf.inputs:
        bsdf.inputs['Transmission Weight'].default_value = transmission
    elif 'Transmission' in bsdf.inputs:
        bsdf.inputs['Transmission'].default_value = transmission
        
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    if tex_filename:
        tex_path = os.path.join(texture_dir, tex_filename)
        if os.path.exists(tex_path):
            img = bpy.data.images.load(tex_path)
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.location = (-400, 0)
            tex_node.image = img
            links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
            print(f"Loaded texture for {name}: {tex_filename}")
            
    return mat

# Create materials
mat_parquet = create_pbr_mat("Mat_ParquetWood", roughness=0.25, tex_filename="Finishes.Flooring.Wood.Parquet.1.jpg")
mat_velvet = create_pbr_mat("Mat_VelvetRed", roughness=0.7, tex_filename="Furnishings.Fabrics.Velvet.Red.jpg")
mat_cocobolo = create_pbr_mat("Mat_CocoboloWood", roughness=0.3, tex_filename="Woods&Plastics.FinishCarpentry.Wood.Cocobolo.jpg")
mat_linen = create_pbr_mat("Mat_LinenBeige", roughness=0.6, tex_filename="Furnishings.Fabrics.Linen.Beige.png")
mat_marble = create_pbr_mat("Mat_CarraraMarble", color=(0.93, 0.93, 0.95, 1.0), roughness=0.15)
mat_gold = create_pbr_mat("Mat_BrushedBrass", color=(1.0, 0.82, 0.38, 1.0), metallic=1.0, roughness=0.18)
mat_chrome = create_pbr_mat("Mat_PolishedChrome", color=(0.95, 0.95, 0.97, 1.0), metallic=1.0, roughness=0.08)
mat_wall = create_pbr_mat("Mat_WallPlaster", color=(0.88, 0.87, 0.85, 1.0), roughness=0.6)
mat_concrete = create_pbr_mat("Mat_Concrete", roughness=0.8, tex_filename="Concrete.Cast-In-Place.Exposed Aggregate.Coarse.jpg")
mat_glass = create_pbr_mat("Mat_ArchitecturalGlass", color=(0.95, 0.98, 1.0, 1.0), roughness=0.03, transmission=0.92)

# 1. FLOOR (24m x 16m)
bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = "Arch_Floor_Parquet"
floor.scale = (24, 16, 1)
bpy.ops.object.transform_apply(scale=True)
floor.data.materials.append(mat_parquet)

# 2. CEILING (Coffered Vault, 24m x 16m at Z=8m)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 8.2))
ceiling = bpy.context.active_object
ceiling.name = "Arch_Ceiling"
ceiling.scale = (24.4, 16.4, 0.4)
bpy.ops.object.transform_apply(scale=True)
ceiling.data.materials.append(mat_wall)

# Build Coffered Ceiling beams (grid of ornate stepped beams)
for x in [-9, -6, -3, 0, 3, 6, 9]:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, 0, 7.9))
    beam = bpy.context.active_object
    beam.name = f"Ceiling_Beam_X_{x}"
    beam.scale = (0.45, 16.0, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    beam.data.materials.append(mat_marble)

for y in [-6, -3, 0, 3, 6]:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, y, 7.9))
    beam = bpy.context.active_object
    beam.name = f"Ceiling_Beam_Y_{y}"
    beam.scale = (24.0, 0.45, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    beam.data.materials.append(mat_marble)

# 3. WALLS & ARBITRARY GRAND ARCHED WINDOWS
# Back Wall (X = +12)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(12.1, 0, 4.0))
wall_back = bpy.context.active_object
wall_back.name = "Arch_Wall_Back"
wall_back.scale = (0.2, 16.0, 8.0)
bpy.ops.object.transform_apply(scale=True)
wall_back.data.materials.append(mat_wall)

# Front Wall (X = -12)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-12.1, 0, 4.0))
wall_front = bpy.context.active_object
wall_front.name = "Arch_Wall_Front"
wall_front.scale = (0.2, 16.0, 8.0)
bpy.ops.object.transform_apply(scale=True)
wall_front.data.materials.append(mat_wall)

# Side Walls (Y = +8 and Y = -8) with Arched Window Openings
for side_y, side_name in [(8.1, "North"), (-8.1, "South")]:
    # Solid Wall baseline
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, side_y, 4.0))
    wall = bpy.context.active_object
    wall.name = f"Arch_Wall_{side_name}"
    wall.scale = (24.0, 0.2, 8.0)
    bpy.ops.object.transform_apply(scale=True)
    wall.data.materials.append(mat_wall)

    # Windows on this side (4 arched grand windows)
    for wx in [-7.5, -2.5, 2.5, 7.5]:
        # Glass pane
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(wx, side_y * 0.99, 4.2))
        glass = bpy.context.active_object
        glass.name = f"Window_Glass_{side_name}_{wx}"
        glass.rotation_euler = (math.radians(90), 0, 0)
        glass.scale = (3.2, 5.0, 1.0)
        bpy.ops.object.transform_apply(rotation=True, scale=True)
        glass.data.materials.append(mat_glass)

        # Window Frame (outer frame)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(wx, side_y * 0.98, 4.2))
        frame = bpy.context.active_object
        frame.name = f"Window_Frame_{side_name}_{wx}"
        frame.scale = (3.4, 0.25, 5.2)
        bpy.ops.object.transform_apply(scale=True)
        frame.data.materials.append(mat_gold)

# 4. GRAND FLUTED COLUMNS (8 Classical Corinthian / Doric Columns)
# Columns at X in [-7.5, -2.5, 2.5, 7.5], Y in [-4.5, 4.5]
def build_classical_column(col_x, col_y, col_id):
    # Base Plinth (Stepped squares)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(col_x, col_y, 0.15))
    plinth1 = bpy.context.active_object
    plinth1.name = f"Col_{col_id}_Plinth1"
    plinth1.scale = (1.4, 1.4, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    plinth1.data.materials.append(mat_marble)

    bpy.ops.mesh.primitive_cylinder_add(vertices=36, radius=0.62, depth=0.25, location=(col_x, col_y, 0.42))
    torus_base = bpy.context.active_object
    torus_base.name = f"Col_{col_id}_BaseRing"
    torus_base.data.materials.append(mat_marble)

    # Fluted Shaft (Cylinder with high polygon count for flutes)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.50, depth=6.5, location=(col_x, col_y, 3.8))
    shaft = bpy.context.active_object
    shaft.name = f"Col_{col_id}_Shaft"
    shaft.data.materials.append(mat_marble)

    # Capital (stepped torus + abacus)
    bpy.ops.mesh.primitive_cylinder_add(vertices=36, radius=0.65, depth=0.35, location=(col_x, col_y, 7.2))
    cap_ring = bpy.context.active_object
    cap_ring.name = f"Col_{col_id}_CapRing"
    cap_ring.data.materials.append(mat_marble)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(col_x, col_y, 7.5))
    abacus = bpy.context.active_object
    abacus.name = f"Col_{col_id}_Abacus"
    abacus.scale = (1.35, 1.35, 0.25)
    bpy.ops.object.transform_apply(scale=True)
    abacus.data.materials.append(mat_marble)

col_count = 0
for cx in [-7.5, -2.5, 2.5, 7.5]:
    for cy in [-4.5, 4.5]:
        col_count += 1
        build_classical_column(cx, cy, col_count)

# 5. CENTERPIECE MASTER ROTUNDA & HIGH-POLY SCULPTURE
# Rotunda Stepped Marble Pedestal
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=2.4, depth=0.35, location=(0, 0, 0.17))
rotunda_base = bpy.context.active_object
rotunda_base.name = "Center_Rotunda_Base"
rotunda_base.data.materials.append(mat_marble)

bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1.6, depth=0.6, location=(0, 0, 0.65))
pedestal = bpy.context.active_object
pedestal.name = "Center_Pedestal"
pedestal.data.materials.append(mat_cocobolo)

# Intricate Centerpiece Geometry: High-poly Torus Knot / Kinetic CAD Sculpture
bpy.ops.mesh.primitive_torus_add(major_radius=1.1, minor_radius=0.32, major_segments=64, minor_segments=32, location=(0, 0, 2.2))
torus1 = bpy.context.active_object
torus1.name = "Sculpture_Torus_Inner"
torus1.rotation_euler = (math.radians(45), math.radians(30), 0)
torus1.data.materials.append(mat_gold)

bpy.ops.mesh.primitive_torus_add(major_radius=1.6, minor_radius=0.22, major_segments=64, minor_segments=32, location=(0, 0, 2.2))
torus2 = bpy.context.active_object
torus2.name = "Sculpture_Torus_Outer"
torus2.rotation_euler = (math.radians(-35), math.radians(60), 0)
torus2.data.materials.append(mat_chrome)

# Center Gem / Sphere
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=0.65, location=(0, 0, 2.2))
center_sphere = bpy.context.active_object
center_sphere.name = "Sculpture_Core_Gem"
center_sphere.data.materials.append(mat_glass)

# 6. LUXURY LOUNGE FURNITURE (4 Designer Armchairs + Round Coffee Table)
# Coffee table at center
bpy.ops.mesh.primitive_cylinder_add(vertices=36, radius=1.0, depth=0.08, location=(0, 0, 0.45))
table_glass = bpy.context.active_object
table_glass.name = "Lounge_CoffeeTable_Glass"
table_glass.data.materials.append(mat_glass)

bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.15, depth=0.45, location=(0, 0, 0.22))
table_base = bpy.context.active_object
table_base.name = "Lounge_CoffeeTable_Base"
table_base.data.materials.append(mat_gold)

# 4 Designer Chairs around the sculpture
chair_angles = [0, 90, 180, 270]
chair_dist = 4.2
for idx, ang_deg in enumerate(chair_angles):
    ang_rad = math.radians(ang_deg)
    chair_x = chair_dist * math.cos(ang_rad)
    chair_y = chair_dist * math.sin(ang_rad)
    facing_rot = ang_rad + math.pi  # face toward center

    # Cushion seat
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(chair_x, chair_y, 0.45))
    seat = bpy.context.active_object
    seat.name = f"Chair_{idx}_Seat"
    seat.rotation_euler = (0, 0, facing_rot)
    seat.scale = (1.1, 1.1, 0.25)
    bpy.ops.object.transform_apply(rotation=True, scale=True)
    seat.data.materials.append(mat_velvet)

    # Backrest
    bx = chair_x + 0.45 * math.cos(ang_rad)
    by = chair_y + 0.45 * math.sin(ang_rad)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(bx, by, 0.95))
    back = bpy.context.active_object
    back.name = f"Chair_{idx}_Back"
    back.rotation_euler = (0, 0, facing_rot)
    back.scale = (1.1, 0.22, 0.8)
    bpy.ops.object.transform_apply(rotation=True, scale=True)
    back.data.materials.append(mat_velvet)

    # Chrome tubular legs
    for lx_off in [-0.45, 0.45]:
        for ly_off in [-0.45, 0.45]:
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.035, depth=0.4, location=(chair_x + lx_off, chair_y + ly_off, 0.2))
            leg = bpy.context.active_object
            leg.name = f"Chair_{idx}_Leg_{lx_off}_{ly_off}"
            leg.data.materials.append(mat_chrome)

# 7. GRAND CHANDELIER (Nested Brass Rings with Crystal Lights at Z=6.5)
bpy.ops.mesh.primitive_torus_add(major_radius=2.2, minor_radius=0.06, major_segments=48, minor_segments=16, location=(0, 0, 6.2))
chan_ring1 = bpy.context.active_object
chan_ring1.name = "Chandelier_Ring_Outer"
chan_ring1.data.materials.append(mat_gold)

bpy.ops.mesh.primitive_torus_add(major_radius=1.4, minor_radius=0.05, major_segments=36, minor_segments=16, location=(0, 0, 5.8))
chan_ring2 = bpy.context.active_object
chan_ring2.name = "Chandelier_Ring_Inner"
chan_ring2.data.materials.append(mat_gold)

# Chandelier suspension cable
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.025, depth=2.0, location=(0, 0, 7.1))
chan_cable = bpy.context.active_object
chan_cable.name = "Chandelier_Cable"
chan_cable.data.materials.append(mat_chrome)

# Chandelier crystal bulbs (12 bulbs on outer ring)
for b_idx in range(12):
    b_ang = b_idx * (2 * math.pi / 12)
    bx = 2.2 * math.cos(b_ang)
    by = 2.2 * math.sin(b_ang)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.09, location=(bx, by, 6.1))
    bulb = bpy.context.active_object
    bulb.name = f"Chandelier_Bulb_{b_idx}"
    bulb.data.materials.append(mat_glass)

# 8. SCENE STATS & EXPORT TO GLB
total_verts = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
total_polys = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
print(f"==================================================")
print(f"SCENE ASSEMBLED SUCCESSFULLY:")
print(f"Total Mesh Objects: {len([o for o in bpy.data.objects if o.type == 'MESH'])}")
print(f"Total Vertices:     {total_verts:,}")
print(f"Total Polygons:     {total_polys:,} (~ {total_polys * 2:,} Triangles)")
print(f"==================================================")

output_glb = os.path.abspath(r"d:\Geometry soft\models\unreal_arch_scene.glb")
output_obj = os.path.abspath(r"d:\Geometry soft\models\unreal_arch_scene.obj")

print(f"Exporting to GLB: {output_glb}...")
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_materials='EXPORT',
    export_image_format='AUTO',
    export_normals=True
)
print("GLB export complete!")

print(f"Exporting to OBJ: {output_obj}...")
bpy.ops.wm.obj_export(filepath=output_obj)
print("OBJ export complete!")
print("=== FINISHED BUILDING UNREAL ARCHITECTURAL SCENE ===")
