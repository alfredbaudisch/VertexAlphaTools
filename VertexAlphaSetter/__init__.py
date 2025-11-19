bl_info = {
    "name": "Vertex Alpha Setter",
    "author": "Matías Avilés Pollak",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Tools",
    "description": "Paints Alpha Vertex in a specific tone",
    "doc_url": "https://github.com/Desayuno64/VertexAlphaSetter",
    "category": "Vertex Paint",
}

from . import VertexAlphaSetter

def register():
    VertexAlphaSetter.register()

def unregister():
    VertexAlphaSetter.unregister()

if __name__ == "__main__":
    register()

