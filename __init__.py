bl_info = {
    "name": "Vertex Alpha Viewer",
    "author": "Alfred R Baudisch",
    "version": (1, 1, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Object > Display Vertex Alpha",
    "description": "Quickly display vertex alpha channel as grayscale",
    "category": "Material",
}

import bpy
from . import vertex_alpha_operator

def register():
    vertex_alpha_operator.register()

def unregister():
    vertex_alpha_operator.unregister()

if __name__ == "__main__":
    register()