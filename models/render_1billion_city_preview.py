import bpy
import math
import os
import time

print("=== RE-RENDERING 1 BILLION CITY METROPOLIS ===")

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Master Skyscraper Tower
# Base Podiums
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 15.0))
podium = bpy.context.active_object
podium.scale = (32.0, 32.0, 30.0)
bpy.ops.object.transform_apply(scale=True)

# Main Shaft
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 95.0))
shaft = bpy.context.active_object
shaft.scale = (22.0, 22.0, 130.0)
bpy.ops.object.transform_apply(scale=True)

# Upper Tier
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 180.0))
tier = bpy.context.active_object
tier.scale = (16.0, 16.0, 40.0)
bpy.ops.object.transform_apply(scale=True)

# Crown & Needle Spire
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=6.0, depth=30.0, location=(0, 0, 215.0))
crown = bpy.context.active_object

bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=3.5, radius2=0.0, depth=70.0, location=(0, 0, 265.0))
spire = bpy.context.active_object

# Join into single master archetype
bpy.ops.object.select_all(action='DESELECT')
for o in [podium, shaft, tier, crown, spire]:
    o.select_set(True)
bpy.context.view_layer.objects.active = podium
bpy.ops.object.join()
master_tower = bpy.context.active_object
master_tower.name = "Master_Skyscraper"

# Glass & Steel PBR Material
mat_facade = bpy.data.materials.new(name="Mat_CityFacade")
mat_facade.use_nodes = True
bsdf = mat_facade.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.22, 0.45, 0.70, 1.0) # Reflective steel-blue glass
    bsdf.inputs['Metallic'].default_value = 0.92
    bsdf.inputs['Roughness'].default_value = 0.15
master_tower.data.materials.append(mat_facade)

# 2. Replicate across City Grid (X and Y are horizontal in Blender, Z is UP)
grid_size = 14
spacing = 90.0

for gx in range(grid_size):
    for gy in range(grid_size):
        if gx == 0 and gy == 0:
            continue
        cx = (gx - grid_size / 2.0 + 0.5) * spacing
        cy = (gy - grid_size / 2.0 + 0.5) * spacing
        h_var = 0.7 + 0.6 * math.sin(gx * 0.7) * math.cos(gy * 0.5)
        
        tower_inst = master_tower.copy()
        tower_inst.data = master_tower.data
        tower_inst.location = (cx, cy, 0.0) # Firmly on the ground Z=0!
        tower_inst.scale = (1.0, 1.0, h_var)
        bpy.context.collection.objects.link(tower_inst)

# 3. Ground Pavement with Grid Lines
bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, -0.2))
ground = bpy.context.active_object
ground.name = "Metropolis_Ground"
ground.scale = (2000.0, 2000.0, 1.0)
bpy.ops.object.transform_apply(scale=True)

mat_ground = bpy.data.materials.new(name="Mat_CityGround")
mat_ground.use_nodes = True
bsdf_g = mat_ground.node_tree.nodes.get("Principled BSDF")
if bsdf_g:
    bsdf_g.inputs['Base Color'].default_value = (0.05, 0.07, 0.10, 1.0)
    bsdf_g.inputs['Roughness'].default_value = 0.3
ground.data.materials.append(mat_ground)

# 4. Cinematic Sunset Atmospheric Sky
world = bpy.data.worlds.new("CitySky")
bpy.context.scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs['Color'].default_value = (0.08, 0.12, 0.25, 1.0) # Deep twilight blue
    bg_node.inputs['Strength'].default_value = 1.8

# Warm Golden Sunset Sun
sun_data = bpy.data.lights.new(name="SunsetSun", type='SUN')
sun_data.energy = 8.0
sun_data.color = (1.0, 0.72, 0.38) # Rich golden orange
sun_obj = bpy.data.objects.new(name="SunsetSun", object_data=sun_data)
sun_obj.rotation_euler = (math.radians(65), math.radians(20), math.radians(125))
bpy.context.collection.objects.link(sun_obj)

# 5. Panoramic High-Angle Camera
cam_data = bpy.data.cameras.new(name="CityCamera")
cam_data.lens = 22 # Ultra wide cinematic lens
cam_obj = bpy.data.objects.new(name="CityCamera", object_data=cam_data)
cam_obj.location = (550.0, -750.0, 420.0)

# Point toward downtown core
direction = -cam_obj.location + bpy.data.objects["Master_Skyscraper"].location
cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
bpy.context.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# 6. Render
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.image_settings.file_format = 'PNG'

out_img = r"d:\Geometry soft\models\megacity_1billion_preview.png"
art_img = r"C:\Users\shaxz\.gemini\antigravity3\brain\1cee2c93-eb3e-436f-bb2d-fb024a44750a\megacity_1billion_preview.png"

bpy.context.scene.render.filepath = out_img
print(f"Rendering 1 Billion City visual preview to {out_img}...")
bpy.ops.render.render(write_still=True)
print("Render finished!")

import shutil
shutil.copyfile(out_img, art_img)
print(f"Copied to {art_img}")
print("=== COMPLETED ===")
