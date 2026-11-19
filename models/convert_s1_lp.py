import json
import base64
import numpy as np

with open(r'd:\Geometry soft\models\s_1_lp_mesh.json', 'r') as f:
    data = json.load(f)

v_bytes = np.array(data['v'], dtype=np.float32).tobytes()
n_bytes = np.array(data['n'], dtype=np.float32).tobytes()
b_bytes = np.array(data['b'], dtype=np.float32).tobytes()
i_bytes = np.array(data['i'], dtype=np.uint16).tobytes()

v_b64 = base64.b64encode(v_bytes).decode('ascii')
n_b64 = base64.b64encode(n_bytes).decode('ascii')
b_b64 = base64.b64encode(b_bytes).decode('ascii')
i_b64 = base64.b64encode(i_bytes).decode('ascii')

js_content = f"""// S_1_LP Blender Model Embedded Payload
window.S1_LP_DATA = {{
  v: "{v_b64}",
  n: "{n_b64}",
  b: "{b_b64}",
  i: "{i_b64}",
  tris: {data['tris']},
  center: {data['center']},
  radius: {data['radius']}
}};

window.getS1LPMesh = function() {{
  const b64toBuffer = (b64) => {{
    const bin = atob(b64);
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    return buf.buffer;
  }};
  return {{
    v: new Float32Array(b64toBuffer(window.S1_LP_DATA.v)),
    n: new Float32Array(b64toBuffer(window.S1_LP_DATA.n)),
    b: new Float32Array(b64toBuffer(window.S1_LP_DATA.b)),
    i: new Uint16Array(b64toBuffer(window.S1_LP_DATA.i)),
    tris: window.S1_LP_DATA.tris,
    center: window.S1_LP_DATA.center,
    radius: window.S1_LP_DATA.radius
  }};
}};
"""

with open(r'd:\Geometry soft\models\s_1_lp_b64.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f"Generated s_1_lp_b64.js ({len(js_content):,} bytes) with {data['tris']} triangles!")
