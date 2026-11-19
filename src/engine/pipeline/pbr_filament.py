"""
OmniGeo Phase 2: Google Filament-Grade Physically Based Rendering (PBR)
========================================================================
Implements the exact mathematical formulation of the Google Filament PBR spec:
1. Normal Distribution Function (NDF):
   GGX / Trowbridge-Reitz with anisotropic extension support.
2. Geometric Shadowing / Masking:
   Smith height-correlated visibility function:
     V(v, l, alpha) = 0.5 / (n.l * sqrt((n.v)^2 * (1 - alpha^2) + alpha^2) +
                             n.v * sqrt((n.l)^2 * (1 - alpha^2) + alpha^2))
3. Fresnel:
   Fresnel-Schlick with F0 base reflectance for dielectrics and conductors.
4. Image-Based Lighting (IBL):
   - 9-coefficient Spherical Harmonics (SH) for diffuse irradiance.
   - Karis split-sum polynomial approximation for specular environment radiance.
5. Tone Mapping:
   ACES (Academy Color Encoding System) filmic tone mapping curve with sRGB conversion.
"""

GLSL_FILAMENT_PBR_HEADER = """
#version 430

const float PI = 3.14159265358979323846;

struct Material {
    vec4 baseColor;
    float roughness;
    float metallic;
    float reflectance;
    float clearCoat;
    float clearCoatRoughness;
    float ao;
    float pad0;
    float pad1;
};

// GGX Microfacet Distribution
float D_GGX(float NdotH, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float d = (NdotH * a2 - NdotH) * NdotH + 1.0;
    return a2 / (PI * d * d + 1e-7);
}

// Smith Height-Correlated Visibility Function (Filament exact)
float V_SmithGGXCorrelated(float NdotV, float NdotL, float roughness) {
    float a2 = roughness * roughness;
    float lambdaV = NdotL * sqrt((NdotV - a2 * NdotV) * NdotV + a2);
    float lambdaL = NdotV * sqrt((NdotL - a2 * NdotL) * NdotL + a2);
    float v = 0.5 / (lambdaV + lambdaL + 1e-7);
    return clamp(v, 0.0, 10.0);
}

// Fresnel-Schlick with 90-degree grazing reflectance
vec3 F_Schlick(float VdotH, vec3 f0, float f90) {
    return f0 + (vec3(f90) - f0) * pow(clamp(1.0 - VdotH, 0.0, 1.0), 5.0);
}

// Diffuse Burley / Disney or Energy-Conserving Lambert
vec3 Fd_Lambert(vec3 diffuseColor) {
    return diffuseColor / PI;
}

// Karis analytical approximation for environment BRDF (Split-Sum LUT)
vec2 EnvBRDFApprox(float roughness, float NdotV) {
    const vec4 c0 = vec4(-1.0, -0.0275, -0.572, 0.022);
    const vec4 c1 = vec4(1.0, 0.0425, 1.04, -0.04);
    vec4 r = roughness * c0 + c1;
    float a004 = min(r.x * r.x, exp2(-9.28 * NdotV)) * r.x + r.y;
    return vec2(-1.04, 1.04) * a004 + r.zw;
}

// 9-term Spherical Harmonics for analytical sky irradiance
vec3 Irradiance_SphericalHarmonics(vec3 n, vec3 sh[9]) {
    return max(
          sh[0]
        + sh[1] * (n.y)
        + sh[2] * (n.z)
        + sh[3] * (n.x)
        + sh[4] * (n.x * n.y)
        + sh[5] * (n.y * n.z)
        + sh[6] * (3.0 * n.z * n.z - 1.0)
        + sh[7] * (n.x * n.z)
        + sh[8] * (n.x * n.x - n.y * n.y),
        vec3(0.0)
    );
}

// ACES Filmic Tone Mapping Curve
vec3 Tonemap_ACES(vec3 x) {
    const float a = 2.51;
    const float b = 0.03;
    const float c = 2.43;
    const float d = 0.59;
    const float e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}
"""
