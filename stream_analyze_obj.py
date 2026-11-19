import os
import time

obj_path = r"C:\Users\shaxz\Downloads\Untitled.obj"

print(f"Streaming analysis of {obj_path}...")
t0 = time.time()

current_obj = "default"
obj_faces = {}
obj_verts = {}

with open(obj_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if line.startswith("o ") or line.startswith("g "):
            current_obj = line.split(maxsplit=1)[1].strip()
            if current_obj not in obj_faces:
                obj_faces[current_obj] = 0
                obj_verts[current_obj] = 0
        elif line.startswith("f "):
            obj_faces[current_obj] = obj_faces.get(current_obj, 0) + 1
        elif line.startswith("v "):
            obj_verts[current_obj] = obj_verts.get(current_obj, 0) + 1

t1 = time.time()
print(f"Analyzed {len(obj_faces)} objects in {t1 - t0:.2f}s:")

# Sort by face count descending
sorted_objs = sorted(obj_faces.items(), key=lambda x: x[1], reverse=True)
print("\nTop 25 Objects by Face Count:")
for name, count in sorted_objs[:25]:
    v_c = obj_verts.get(name, 0)
    print(f"  {name:30s}: {count:,} faces ({v_c:,} local verts)")

total_f = sum(obj_faces.values())
print(f"\nTotal Faces across all objects: {total_f:,}")
