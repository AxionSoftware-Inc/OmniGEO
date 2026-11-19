import os
import sys
import time

obj_path = r"C:\Users\shaxz\Downloads\Untitled.obj"
mtl_path = r"C:\Users\shaxz\Downloads\Untitled.mtl"

print(f"Inspecting OBJ: {obj_path}")
print(f"File size: {os.path.getsize(obj_path):,} bytes")

t0 = time.time()
v_count = 0
vn_count = 0
vt_count = 0
f_count = 0
o_names = []

with open(obj_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if line.startswith("v "):
            v_count += 1
        elif line.startswith("vn "):
            vn_count += 1
        elif line.startswith("vt "):
            vt_count += 1
        elif line.startswith("f "):
            f_count += 1
        elif line.startswith("o ") or line.startswith("g "):
            name = line.split(maxsplit=1)[1].strip()
            if len(o_names) < 30:
                o_names.append(name)

t1 = time.time()
print(f"Scanned in {t1 - t0:.2f} seconds:")
print(f"  Vertices (v):  {v_count:,}")
print(f"  Normals (vn):  {vn_count:,}")
print(f"  UVs (vt):      {vt_count:,}")
print(f"  Faces (f):     {f_count:,}")
print(f"  Objects sample ({len(o_names)}): {o_names[:10]}")
