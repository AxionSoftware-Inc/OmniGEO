import bpy
import os
import time

print("=== STARTING HIGH-FIDELITY USER SCENE IMPORTER & RENDERER ===")

obj_path = r"C:\Users\shaxz\Downloads\Untitled.obj"
mtl_path = r"C:\Users\shaxz\Downloads\Untitled.mtl"

# Clear factory settings
bpy.ops.wm.read_factory_settings(use_empty=True)

t0 = time.time()
print(f"Importing {obj_path} via fast C++ obj_import...")
bpy.ops.wm.obj_import(filepath=obj_path)
t_import = time.time() - t0
print(f"Import finished in {t_import:.2f} seconds!")

# Inspect imported geometry
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
total_verts = sum(len(o.data.vertices) for o in mesh_objs)
total_polys = sum(len(o.data.polygons) for o in mesh_objs)

print(f"Imported Objects:  {len(mesh_objs):,}")
print(f"Total Vertices:    {total_verts:,}")
print(f"Total Polygons:    {total_polys:,}")

# Calculate scene bounding box
import mathutils
min_coord = mathutils.Vector((float('inf'), float('inf'), float('inf')))
max_coord = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))

for obj in mesh_objs:
    for corner in [obj.matrix_world @ mathutils.Vector(b) for b in obj.bound_box]:
        min_coord.x = min(min_coord.x, corner.x)
        min_coord.y = min(min_coord.y, corner.y)
        min_coord.z = min(min_coord.z, corner.z)
        max_coord.x = max(max_coord.x, corner.x)
        max_coord.y = max(max_coord.y, corner.y)
        max_coord.z = max(max_coord.z, corner.z)

center = (min_coord + max_coord) * 0.5
size = max_coord - min_coord
max_dim = max(size.x, size.y, size.z)

print(f"Scene Bounding Box: Min={min_coord}, Max={max_coord}")
print(f"Scene Dimensions:   {size} (MaxDim={max_dim:.2f})")
print(f"Scene Center:       {center}")

# SETUP LIGHTING (Photorealistic Daylight Interior)
# 1. World Background (HDRI Ambient Sky)
world = bpy.data.worlds.new("DaylightWorld")
bpy.context.scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs['Color'].default_value = (0.75, 0.85, 1.0, 1.0)
    bg_node.inputs['Strength'].default_value = 2.5 # Strong ambient daylight fill

# 2. Sun Light (Angled through windows)
sun_data = bpy.data.lights.new(name="SunLight", type='SUN')
sun_data.energy = 5.0
sun_data.color = (1.0, 0.96, 0.90)
sun_obj = bpy.data.objects.new(name="SunLight", object_data=sun_data)
sun_obj.location = (center.x + max_dim * 0.5, center.y - max_dim * 0.5, center.z + max_dim * 0.8)
sun_obj.rotation_euler = (0.7, 0.4, 0.8)
bpy.context.collection.objects.link(sun_obj)

# 3. Interior Fill Lights (Placed at center and high corners so no room is pitch black)
for i, offset in enumerate([
    (0, 0, size.z * 0.4),
    (-size.x * 0.25, 0, size.z * 0.3),
    (size.x * 0.25, 0, size.z * 0.3),
    (0, -size.y * 0.25, size.z * 0.3),
    (0, size.y * 0.25, size.z * 0.3)
]):
    fill_data = bpy.data.lights.new(name=f"FillLight_{i}", type='POINT')
    fill_data.energy = 8000.0
    fill_data.color = (1.0, 0.92, 0.82)
    fill_data.shadow_soft_size = 1.5
    fill_obj = bpy.data.objects.new(name=f"FillLight_{i}", object_data=fill_data)
    fill_obj.location = (center.x + offset[0], center.y + offset[1], center.z + offset[2])
    bpy.context.collection.objects.link(fill_obj)

# 4. Setup Camera
cam_data = bpy.data.cameras.new(name="RenderCamera")
cam_data.lens = 28 # Wide architectural lens
cam_obj = bpy.data.objects.new(name="RenderCamera", object_data=cam_data)
# Place camera overlooking scene
cam_obj.location = (center.x - size.x * 0.35, center.y - size.y * 0.55, center.z + size.z * 0.5)
# Point at center
direction = center - cam_obj.location
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()
bpy.context.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# RENDER A TEST IMAGE VIA EEVEE / WORKBENCH
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.image_settings.file_format = 'PNG'

render_png = r"d:\Geometry soft\models\user_scene_preview.png"
bpy.context.scene.render.filepath = render_png

print(f"Rendering photorealistic visual preview to {render_png}...")
bpy.ops.render.render(write_still=True)
print(f"Render complete: {render_png}")

# Save project file
blend_file = r"d:\Geometry soft\models\user_scene_full.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_file)
print(f"Saved Blender file: {blend_file}")
print("=== FINISHED IMPORT & RENDER ===")
