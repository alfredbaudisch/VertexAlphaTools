bl_info = {
    "name": "Vertex Alpha Tools",
    "author": "Alfred R Baudisch",
    "version": (2, 3, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Tool > Vertex Alpha Setter",
    "description": "Set vertex alpha values and toggle vertex alpha visualization",
    "category": "Vertex Paint",
}

import bpy
from . import vertex_alpha_operator
from . import VertexAlphaSetter

def register():
    vertex_alpha_operator.register()
    VertexAlphaSetter.register()

def unregister():
    vertex_alpha_operator.unregister()
    VertexAlphaSetter.unregister()

if __name__ == "__main__":
    register()