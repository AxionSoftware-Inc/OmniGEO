import bpy
import os
import time

print("=== OPTIMIZING & EXPORTING CLEAN USER SCENE GLB ===")

blend_file = r"d:\Geometry soft\models\user_scene_full.blend"
bpy.ops.wm.open_mainfile(filepath=blend_file)

mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
print(f"Total objects in blend: {len(mesh_objs):,}")

# Intelligently decimate ONLY excessively dense objects (like foliage with 300k faces)
# Keep all architectural objects, signs, tables, cups, cupcakes pristine!
decimated_count = 0
for obj in mesh_objs:
    poly_count = len(obj.data.polygons)
    if poly_count > 60_000:
        # High-density foliage / sphere
        ratio = max(0.08, 25_000.0 / poly_count)
        mod = obj.modifiers.new(name="AutoLOD", type='DECIMATE')
        mod.ratio = ratio
        decimated_count += 1
    elif poly_count > 20_000:
        ratio = 0.35
        mod = obj.modifiers.new(name="AutoLOD", type='DECIMATE')
        mod.ratio = ratio
        decimated_count += 1

print(f"Applied intelligent LOD decimation to {decimated_count} high-density foliage/sphere objects.")

# Export clean GLB
glb_out = r"d:\Geometry soft\models\user_scene_clean.glb"
t0 = time.time()
print(f"Exporting GLB to {glb_out}...")

bpy.ops.export_scene.gltf(
    filepath=glb_out,
    export_format='GLB',
    export_apply=True, # Apply modifiers
    export_materials='EXPORT',
    export_normals=True
)

t1 = time.time()
glb_size = os.path.getsize(glb_out)
print(f"GLB Export finished in {t1 - t0:.2f}s! Size: {glb_size:,} bytes ({glb_size / 1024 / 1024:.2f} MB)")

# Also copy to web folder
import shutil
web_glb = r"d:\Geometry soft\web\user_scene_clean.glb"
shutil.copyfile(glb_out, web_glb)
print(f"Copied to {web_glb}")

# Render a beautiful close-up of the Coffee shop and Cupcake pavilions to verify lighting
cam = bpy.data.objects.get("RenderCamera")
if cam:
    cam.location = (18.0, -12.0, 9.0)
    # Target Coffee shop
    target = (13.0, 7.0, 4.0)
    import mathutils
    dir_vec = mathutils.Vector(target) - cam.location
    cam.rotation_euler = dir_vec.to_track_quat('-Z', 'Y').to_euler()

close_png = r"d:\Geometry soft\models\user_scene_closeup.png"
bpy.context.scene.render.filepath = close_png
bpy.ops.render.render(write_still=True)
print(f"Saved closeup render: {close_png}")
print("=== COMPLETED ===")
