# This module is part of the Vertex Alpha Tools addon
from . import VertexAlphaSetter

# Expose register/unregister functions
def register():
    VertexAlphaSetter.register()

def unregister():
    VertexAlphaSetter.unregister()

