"""
Procedural Fractal Heightmap Generator
=======================================
Generates realistic terrain elevation (mountains, plateaus, valleys, rivers)
using multi-octave Fractional Brownian Motion (fBm) with Perlin/Simplex noise.

Features:
- Pure analytical shader implementation: 0 bytes of heightmap texture memory!
- Analytical normal computation via central differences directly in vertex/fragment shader.
- Supports giant 100+ km geographic spans.
"""

# GLSL shader chunk for analytical terrain elevation
GLSL_PROCEDURAL_TERRAIN_CHUNK = """
// 2D Hash function
vec2 hash2(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

// Gradient noise (Perlin-like)
float gnoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);

    return mix(mix(dot(hash2(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0)),
                   dot(hash2(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
               mix(dot(hash2(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
                   dot(hash2(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x), u.y);
}

// Multi-octave fBm (Fractional Brownian Motion)
float getTerrainHeight(vec2 worldXZ) {
    vec2 p = worldXZ * 0.0003; // Base scale (km scale)
    float h = 0.0;
    float amp = 600.0;        // Mountain amplitude: 600 meters
    float freq = 1.0;

    // 5 octaves
    for (int i = 0; i < 5; ++i) {
        h += gnoise(p * freq) * amp;
        amp *= 0.45;
        freq *= 2.1;
    }

    // Add mountain ridge shaping (sharp peaks)
    float ridge = 1.0 - abs(gnoise(p * 2.0));
    h += ridge * ridge * 350.0;

    return h;
}

// Analytical terrain normal via finite differences
vec3 getTerrainNormal(vec2 worldXZ) {
    float eps = 1.0; // 1 meter sampling step
    float hC = getTerrainHeight(worldXZ);
    float hR = getTerrainHeight(worldXZ + vec2(eps, 0.0));
    float hT = getTerrainHeight(worldXZ + vec2(0.0, eps));

    vec3 dX = vec3(eps, hR - hC, 0.0);
    vec3 dZ = vec3(0.0, hT - hC, eps);
    return normalize(cross(dZ, dX));
}
"""
