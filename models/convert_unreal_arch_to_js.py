import base64
import os
import json

glb_path = r"d:\Geometry soft\models\unreal_arch_scene.glb"
js_out = r"d:\Geometry soft\models\unreal_arch_scene_b64.js"

with open(glb_path, "rb") as f:
    glb_bytes = f.read()

b64_str = base64.b64encode(glb_bytes).decode("ascii")

with open(js_out, "w") as f:
    f.write(f"// Unreal Arch Scene Base64 encoded GLB ({len(glb_bytes):,} bytes)\n")
    f.write(f"window.UNREAL_ARCH_SCENE_B64 = \"{b64_str}\";\n")

print(f"Generated {js_out} ({len(b64_str):,} chars)")
