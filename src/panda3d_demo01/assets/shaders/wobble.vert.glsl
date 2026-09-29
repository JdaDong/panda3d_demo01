#version 120
// =============================================================================
// wobble.vert.glsl —— 顶点着色器：按时间让顶点沿法线“呼吸”
// -----------------------------------------------------------------------------
// Panda3D 会自动绑定以 p3d_ / osg_ 开头的内置 uniform/attribute：
//   p3d_ModelViewProjectionMatrix  模型→裁剪空间
//   p3d_NormalMatrix               法线矩阵（模型视图矩阵逆转置的 3x3）
//   p3d_Vertex / p3d_Normal / p3d_MultiTexCoord0  顶点属性
//   osg_FrameTime                  帧时间（秒），无需 set_shader_input
// 自定义 uniform（amplitude）由 NodePath.set_shader_input("amplitude", x) 传入。
// macOS legacy context 只有 GLSL 1.20，所以使用 attribute/varying 语法。
// =============================================================================
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat3 p3d_NormalMatrix;
uniform float osg_FrameTime;
uniform float amplitude;

attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec2 p3d_MultiTexCoord0;

varying vec3 v_normal;
varying vec2 v_uv;
varying float v_wave;

void main() {
    float wave = sin(p3d_Vertex.z * 4.0 + osg_FrameTime * 3.0);
    vec4 pos = p3d_Vertex + vec4(p3d_Normal * wave * amplitude, 0.0);
    gl_Position = p3d_ModelViewProjectionMatrix * pos;
    v_normal = normalize(p3d_NormalMatrix * p3d_Normal);
    v_uv = p3d_MultiTexCoord0;
    v_wave = wave;
}
