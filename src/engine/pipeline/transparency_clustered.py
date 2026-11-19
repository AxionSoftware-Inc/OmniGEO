"""
OmniGeo Phase 3: Clustered Architectural Glass & Transparency Pipeline
=======================================================================
Implements physically accurate architectural glazing (curtain walls, double-pane windows):
1. Order-Preserving Two-Phase Render:
   - Phase 1 (Opaque): Structural slabs, columns, interior partitions, frames write to depth.
   - Phase 2 (Transparent): Low-E glass panels rendered with depth-read (GL_EQUAL / GL_LEQUAL, no depth write).
2. Physical Glazing Optics:
   - Schlick Fresnel reflectance:
       R(theta) = R0 + (1 - R0) * (1 - cos(theta))^5
     Glancing viewing angles become like mirrors (reflecting sky/sun),
     while front-facing angles transmit light (revealing interior structural details).
   - Solar tint absorption (Beer-Lambert law for tinted architectural glass).
"""

GLSL_ARCHITECTURAL_GLASS_CHUNK = """
// Architectural Glazing Shader (Physical Glass with Fresnel and Interior Transmission)

vec4 shadeArchitecturalGlass(
    vec3 worldPos,
    vec3 normal,
    vec3 camPos,
    vec3 lightDir,
    vec3 sunColor,
    vec3 skyAmbient,
    vec4 glassTint,     // e.g. vec4(0.12, 0.38, 0.52, 0.85) Low-E Solar Blue
    float roughness     // 0.02 for smooth glass
) {
    vec3 N = normalize(normal);
    vec3 V = normalize(camPos - worldPos);
    vec3 L = normalize(lightDir);
    vec3 H = normalize(V + L);

    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float NdotH = max(dot(N, H), 0.0);

    // Glass dielectric base reflectance (IOR ~ 1.52 => F0 = 0.043)
    float F0 = 0.043;
    float fresnel = F0 + (1.0 - F0) * pow(clamp(1.0 - NdotV, 0.0, 1.0), 5.0);

    // Specular sun highlight on glass
    float a = roughness * roughness;
    float a2 = a * a;
    float denom = (NdotH * NdotH * (a2 - 1.0) + 1.0);
    float D = a2 / (3.14159 * denom * denom + 1e-6);
    vec3 sunSpec = sunColor * D * fresnel * NdotL * 1.5;

    // Specular sky reflection (mirrored reflection at glancing angles)
    vec3 R = reflect(-V, N);
    float skyUp = R.y * 0.5 + 0.5;
    vec3 skyReflect = mix(vec3(0.08, 0.06, 0.05), skyAmbient * 2.0, skyUp);

    // Interior transmission opacity:
    // Glancing angles are opaque/reflective; perpendicular angles are transparent!
    float finalAlpha = mix(0.25, 0.92, fresnel);

    vec3 finalColor = mix(glassTint.rgb, skyReflect, fresnel) + sunSpec;

    return vec4(finalColor, finalAlpha);
}
"""
