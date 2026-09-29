#version 120
// =============================================================================
// wobble.frag.glsl —— 片元着色器：卡通分段光照 + 边缘光(rim) + 纹理
// -----------------------------------------------------------------------------
//   p3d_Texture0   当前节点第 0 层纹理（由 set_texture 自动绑定）
//   tint / light_dir 为自定义 uniform
// =============================================================================
uniform sampler2D p3d_Texture0;
uniform vec4 tint;
uniform vec3 light_dir;   // 视图空间下的光方向

varying vec3 v_normal;
varying vec2 v_uv;
varying float v_wave;

void main() {
    vec3 n = normalize(v_normal);
    float ndl = max(dot(n, normalize(-light_dir)), 0.0);
    // 卡通分段：把连续的 ndl 量化成 4 档
    float toon = floor(ndl * 4.0) / 4.0 + 0.15;
    // 视图空间里相机朝 -Z，边缘 = 法线与视线接近垂直
    float rim = pow(1.0 - abs(n.z), 3.0);
    vec4 tex = texture2D(p3d_Texture0, v_uv);
    vec3 color = tex.rgb * tint.rgb * toon + vec3(0.3, 0.6, 1.0) * rim + 0.05 * v_wave;
    gl_FragColor = vec4(color, 1.0);
}
