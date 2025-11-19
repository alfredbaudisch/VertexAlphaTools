import bpy
from bpy.props import StringProperty
from bpy.types import Operator, Material
import blf
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d

_draw_handlers = []

def draw_vertex_alpha_labels():
    """Draw vertex alpha values as text labels in the 3D viewport"""
    context = bpy.context
    
    try:
        # In a 3D Viewport?
        if not hasattr(context, 'space_data') or not context.space_data:
            return
        if context.space_data.type != 'VIEW_3D':
            return
        
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            return
        
        mesh = obj.data
            
        # Does the mesh have vertex colors?
        if not mesh.color_attributes:
            return
        
        # Get the first color attribute
        color_attr = None
        for attr in mesh.color_attributes:
            if attr.data_type == 'BYTE_COLOR' or attr.data_type == 'FLOAT_COLOR':
                color_attr = attr
                break
        
        if not color_attr:
            return
        
        # Get the viewport region
        region = context.region
        region3d = context.space_data.region_3d
        
        if not region or not region3d:
            return
    except Exception as e:
        # Silently fail if context is not available
        return
    
    # Set up font
    font_id = 0
    blf.size(font_id, 24)
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)

    matrix_world = obj.matrix_world
    
    # Vertex positions and alpha values
    vertices = mesh.vertices
    color_data = color_attr.data
    
    # Handle different attribute domains
    is_per_vertex = color_attr.domain == 'POINT'
    
    # For per-corner attributes, build a mapping of vertex to alpha values
    vertex_alpha_map = {}
    if not is_per_vertex:
        # Build mapping: vertex_index -> list of alpha values
        for poly in mesh.polygons:
            for loop_idx in poly.loop_indices:
                vert_idx = mesh.loops[loop_idx].vertex_index
                # In Blender 4.x, BYTE_COLOR values are already normalized to 0.0-1.0
                alpha_val = color_data[loop_idx].color[3]
                
                if vert_idx not in vertex_alpha_map:
                    vertex_alpha_map[vert_idx] = []
                vertex_alpha_map[vert_idx].append(alpha_val)
    
    # Draw text for each vertex
    for i, vert in enumerate(vertices):
        # Get world position
        world_pos = matrix_world @ vert.co
        
        # Project to 2D screen coordinates
        try:
            screen_pos = location_3d_to_region_2d(region, region3d, world_pos, default=None)
        except:
            continue
        
        # Skip if vertex is behind camera
        if screen_pos is None:
            continue
        
        # Get alpha value based on domain
        try:
            if is_per_vertex:
                # Per-vertex: direct access
                # In Blender 4.x, both BYTE_COLOR and FLOAT_COLOR are normalized to 0.0-1.0
                color_val = color_data[i].color
                if len(color_val) >= 4:
                    alpha = color_val[3]
                else:
                    alpha = 1.0  # Default if no alpha channel
            else:
                # Per-corner: get average alpha from all corners of this vertex
                if i in vertex_alpha_map and len(vertex_alpha_map[i]) > 0:
                    alpha = sum(vertex_alpha_map[i]) / len(vertex_alpha_map[i])
                else:
                    continue
        except Exception as e:
            # If we can't read alpha, skip this vertex
            continue
        
        # Format alpha value (2 decimal places)
        alpha_text = f"{alpha:.2f}"
        
        # Draw text with shadow for visibility
        # Draw shadow first (offset)
        blf.position(font_id, screen_pos.x + 6, screen_pos.y + 4, 0)
        blf.color(font_id, 0.0, 0.0, 0.0, 1.0)
        blf.draw(font_id, alpha_text)
        
        # Draw text on top
        blf.position(font_id, screen_pos.x + 5, screen_pos.y + 5, 0)
        blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
        blf.draw(font_id, alpha_text)

class VIEW3D_OT_display_vertex_alpha(Operator):
    """Toggle between displaying vertex alpha channel and original material"""
    bl_idname = "view3d.display_vertex_alpha"
    bl_label = "Toggle Vertex Alpha Viewer"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        global _draw_handlers
        
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


class VIEW3D_OT_toggle_vertex_alpha_labels(Operator):
    """Toggle display of vertex alpha values as text labels"""
    bl_idname = "view3d.toggle_vertex_alpha_labels"
    bl_label = "Toggle Vertex Alpha Labels"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        global _draw_handlers
        
        # Check if handlers are currently active
        if _draw_handlers:
            # Remove all handlers
            for handler in _draw_handlers:
                try:
                    bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
                except:
                    pass
            _draw_handlers.clear()
            
            # Request viewport redraw to remove labels
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            self.report({'INFO'}, "Vertex alpha labels hidden")
        else:
            # Add handler
            handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_vertex_alpha_labels,
                (),
                'WINDOW',
                'POST_PIXEL'
            )
            _draw_handlers.append(handler)
            
            # Request viewport redraw to show labels
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            self.report({'INFO'}, "Vertex alpha labels shown")
        
        return {'FINISHED'}


def register():
    bpy.utils.register_class(VIEW3D_OT_display_vertex_alpha)
    bpy.utils.register_class(VIEW3D_OT_toggle_vertex_alpha_labels)


def unregister():
    # Unregister all draw handlers
    global _draw_handlers
    for handler in _draw_handlers:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
        except:
            pass
    _draw_handlers.clear()
    
    bpy.utils.unregister_class(VIEW3D_OT_toggle_vertex_alpha_labels)
    bpy.utils.unregister_class(VIEW3D_OT_display_vertex_alpha)