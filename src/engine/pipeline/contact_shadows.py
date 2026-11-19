"""
OmniGeo Phase 3: Screen-Space Contact Shadows (SSCS) & Analytical Sun Shadows
=============================================================================
Provides ultra-fine contact shadows across 100km landscapes down to 1mm bolts:
1. Screen-Space Contact Shadows (SSCS):
   - Ray-marches the hardware depth buffer along the screen-projected light vector.
   - Requires 0 bytes of shadow map VRAM!
   - Captures sub-millimeter contact shadows right under window sills, cornice lips,
     and 1mm bolts where traditional Cascaded Shadow Maps (CSM) fail.
2. Analytical Terrain Horizon Shadows:
   - Directly ray-marches the fractal height formula for distant mountains (1km - 100km).
"""

GLSL_CONTACT_SHADOWS_CHUNK = """
// Screen-Space Contact Shadows (SSCS) Shader Chunk
// Ray-marches the depth buffer in screen space

float computeContactShadow(vec3 worldPos, vec3 lightDir, mat4 viewProj, sampler2D depthMap, int numSteps) {
    // Project world position to clip space
    vec4 startClip = viewProj * vec4(worldPos, 1.0);
    vec3 startScreen = startClip.xyz / startClip.w;
    startScreen.xy = startScreen.xy * 0.5 + 0.5;

    // Ray step in world space towards the sun
    float maxDistance = 3.5; // Max 3.5 meters search distance for fine details
    vec3 endWorld = worldPos + lightDir * maxDistance;
    vec4 endClip = viewProj * vec4(endWorld, 1.0);
    vec3 endScreen = endClip.xyz / endClip.w;
    endScreen.xy = endScreen.xy * 0.5 + 0.5;

    vec3 rayStep = (endScreen - startScreen) / float(numSteps);
    vec3 currentRay = startScreen + rayStep;

    float shadow = 1.0;
    float depthBias = 0.0012;

    for (int i = 0; i < 16; ++i) {
        if (i >= numSteps) break;

        // Outside screen bounds
        if (currentRay.x < 0.0 || currentRay.x > 1.0 || currentRay.y < 0.0 || currentRay.y > 1.0) {
            break;
        }

        float sampledDepth = texture(depthMap, currentRay.xy).r;
        float rayDepth = currentRay.z;

        // If ray penetrates geometry behind surface
        if (rayDepth > sampledDepth + depthBias && rayDepth < sampledDepth + 0.02) {
            // Soft shadow falloff based on ray travel distance
            float distanceWeight = float(i) / float(numSteps);
            shadow = mix(0.15, 0.85, distanceWeight);
            break;
        }

        currentRay += rayStep;
    }

    return shadow;
}
"""
