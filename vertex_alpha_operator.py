import bpy
from bpy.props import StringProperty
from bpy.types import Operator, Material

class VIEW3D_OT_display_vertex_alpha(Operator):
    """Toggle between displaying vertex alpha channel and original material"""
    bl_idname = "view3d.display_vertex_alpha"
    bl_label = "Display Vertex Alpha"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object")
            return {'CANCELLED'}
        
        mesh = obj.data
        
        # Check if we're currently showing vertex alpha
        # Strategy: Check if any material assigned to this object matches our vertex alpha pattern
        alpha_mat_name = f"{obj.name}_VertexAlpha"
        is_showing_alpha = False
        found_alpha_mat = None
        
        # First, check all materials assigned to this object
        if obj.data.materials:
            for mat_slot in obj.data.materials:
                if mat_slot:
                    mat_name = mat_slot.name
                    # Check if name matches our pattern (this is the primary check)
                    if mat_name.endswith("_VertexAlpha") or mat_name == alpha_mat_name:
                        is_showing_alpha = True
                        found_alpha_mat = mat_slot
                        alpha_mat_name = mat_name
                        break
        
        # Fallback: check active material
        if not is_showing_alpha and obj.active_material:
            active_mat = obj.active_material
            active_mat_name = active_mat.name
            if active_mat_name.endswith("_VertexAlpha") or active_mat_name == alpha_mat_name:
                is_showing_alpha = True
                found_alpha_mat = active_mat
                alpha_mat_name = active_mat_name
        
        # Last resort: check custom property and search all materials
        if not is_showing_alpha:
            try:
                if "_vertex_alpha_active" in obj:
                    prop_value = obj["_vertex_alpha_active"]
                    if bool(prop_value):
                        # Try to find the material in bpy.data.materials
                        for mat in bpy.data.materials:
                            if mat.name.endswith("_VertexAlpha"):
                                # Check if it's assigned to this object
                                if obj.data.materials:
                                    for slot in obj.data.materials:
                                        if slot == mat:
                                            is_showing_alpha = True
                                            found_alpha_mat = mat
                                            alpha_mat_name = mat.name
                                            break
                                    if is_showing_alpha:
                                        break
            except:
                pass
        
        if is_showing_alpha:
            # Restore original material
            original_mat_name = None
            try:
                if "_original_material_name" in obj:
                    original_mat_name = obj["_original_material_name"]
            except:
                original_mat_name = None
            
            # Restore the original material
            if original_mat_name:
                original_mat = bpy.data.materials.get(original_mat_name)
                if original_mat:
                    # Replace the material in the slot
                    if len(obj.data.materials) > 0:
                        obj.data.materials[0] = original_mat
                    else:
                        obj.data.materials.append(original_mat)
                    obj.active_material = original_mat
                    self.report({'INFO'}, f"Restored original material: {original_mat_name}")
                else:
                    # Original material was deleted, clear the slot
                    if len(obj.data.materials) > 0:
                        obj.data.materials.clear()
                    obj.active_material = None
                    self.report({'INFO'}, "Original material no longer exists, cleared material slot")
            else:
                # No original material was saved - clear the material slot
                if len(obj.data.materials) > 0:
                    obj.data.materials.clear()
                obj.active_material = None
                self.report({'INFO'}, "No original material to restore, cleared material slot")
            
            # Remove vertex alpha material
            alpha_mat = bpy.data.materials.get(alpha_mat_name)
            if alpha_mat:
                # Make sure no objects are using this material before removing
                # (though we just replaced it above, so it should be safe)
                bpy.data.materials.remove(alpha_mat)
            
            # Clear custom properties
            if "_vertex_alpha_active" in obj:
                del obj["_vertex_alpha_active"]
            if "_original_material_name" in obj:
                del obj["_original_material_name"]
            
            return {'FINISHED'}
        
        # Check if mesh has vertex colors
        if not mesh.color_attributes:
            self.report({'ERROR'}, "Mesh has no vertex color attributes")
            return {'CANCELLED'}
        
        # Find the first color attribute
        color_attr = None
        for attr in mesh.color_attributes:
            if attr.data_type == 'BYTE_COLOR' or attr.data_type == 'FLOAT_COLOR':
                color_attr = attr
                break
        
        if not color_attr:
            self.report({'ERROR'}, "No color attribute found")
            return {'CANCELLED'}
        
        # Save current material as original (only if it's not already the vertex alpha material)
        current_mat = obj.active_material
        original_mat_name = None
        if current_mat and not current_mat.name.endswith("_VertexAlpha"):
            original_mat_name = current_mat.name
        # If no material or it's the vertex alpha material, original_mat_name stays None
        
        # Get or create vertex alpha material
        mat_name = f"{obj.name}_VertexAlpha"
        mat = bpy.data.materials.get(mat_name)
        
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
        
        # Enable use nodes
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Clear existing nodes
        nodes.clear()
        
        # Create nodes
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (300, 0)
        
        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf_node.location = (0, 0)
        
        # Create Attribute node to get vertex color
        attr_node = nodes.new(type='ShaderNodeAttribute')
        attr_node.attribute_name = color_attr.name
        attr_node.location = (-300, 0)
        
        # Create Combine RGB node to make grayscale from alpha
        combine_node = nodes.new(type='ShaderNodeCombineColor')
        combine_node.location = (-150, -150)
        combine_node.mode = 'RGB'
        
        # Get alpha from the color attribute's alpha channel
        links.new(attr_node.outputs['Alpha'], combine_node.inputs['Red'])
        links.new(attr_node.outputs['Alpha'], combine_node.inputs['Green'])
        links.new(attr_node.outputs['Alpha'], combine_node.inputs['Blue'])
        
        # Connect to Base Color
        links.new(combine_node.outputs['Color'], bsdf_node.inputs['Base Color'])
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
        
        # Assign material to object
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
        
        # Set material as active
        obj.active_material = mat
        
        # Store state in custom properties
        obj["_vertex_alpha_active"] = True
        if original_mat_name:
            obj["_original_material_name"] = original_mat_name
        
        self.report({'INFO'}, f"Displaying vertex alpha (attribute: {color_attr.name})")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(VIEW3D_OT_display_vertex_alpha)
    
    # Add to Object menu
    def menu_func(self, context):
        self.layout.separator()
        self.layout.operator(VIEW3D_OT_display_vertex_alpha.bl_idname)
    
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(VIEW3D_OT_display_vertex_alpha)
    bpy.types.VIEW3D_MT_object.remove(menu_func)