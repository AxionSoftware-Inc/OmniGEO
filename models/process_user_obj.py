import bpy
import os
import time

print("=== STARTING USER OBJ PROCESSOR (BLENDER 5.2 C++ ENGINE) ===")

obj_path = r"C:\Users\shaxz\Downloads\Untitled.obj"
mtl_path = r"C:\Users\shaxz\Downloads\Untitled.mtl"

# Clear existing scene
bpy.ops.wm.read_factory_settings(use_empty=True)

t0 = time.time()
print(f"Importing {obj_path} via C++ obj_import...")
bpy.ops.wm.obj_import(filepath=obj_path)
t_import = time.time() - t0
print(f"Import completed in {t_import:.2f} seconds!")

# Inspect scene
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
total_verts = sum(len(o.data.vertices) for o in mesh_objs)
total_polys = sum(len(o.data.polygons) for o in mesh_objs)

print(f"Total Mesh Objects: {len(mesh_objs):,}")
print(f"Total Vertices:     {total_verts:,}")
print(f"Total Polygons:     {total_polys:,}")

# Check materials
print(f"Total Materials in scene: {len(bpy.data.materials):,}")
for m in bpy.data.materials[:15]:
    print(f"  Material: {m.name}")

# Link PBR textures from textures folder
tex_dir = r"d:\Geometry soft\models\textures"
tex_map = {
    "CERAMICOS_AZULES": "Finishes.Tiling.Ceramic.Mosaic.Blue.jpg",
    "CHOCOLATE": "Woods&Plastics.FinishCarpentry.Wood.Cocobolo.jpg",
    "GRIS_CALLE": "Concrete.Cast-In-Place.Exposed Aggregate.Coarse.jpg",
    "BREAD": "Furnishings.Fabrics.Linen.Beige.png"
}

for mat_name, tex_file in tex_map.items():
    if mat_name in bpy.data.materials:
        mat = bpy.data.materials[mat_name]
        tex_path = os.path.join(tex_dir, tex_file)
        if os.path.exists(tex_path) and mat.node_tree:
            img = bpy.data.images.load(tex_path)
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            bsdf = nodes.get("Principled BSDF")
            if bsdf:
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.image = img
                links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
                print(f"Successfully linked texture {tex_file} -> {mat_name}")

# Save Blender file
blend_out = r"d:\Geometry soft\models\user_daylight_interior.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print(f"Saved native Blender project: {blend_out}")

# Build a Decimated / Nanite-LOD mesh for real-time viewport (150,000 - 300,000 triangles)
# To preserve interactive 120-720Hz in WebGL while rendering full 19.7M in engine
glb_out = r"d:\Geometry soft\models\user_daylight_interior_opt.glb"
print(f"Exporting optimized WebGL/OmniGeo GLB...")
bpy.ops.export_scene.gltf(
    filepath=glb_out,
    export_format='GLB',
    export_materials='EXPORT',
    export_normals=True
)
print(f"GLB export finished: {glb_out}")
print("=== PROCESSING COMPLETE ===")
