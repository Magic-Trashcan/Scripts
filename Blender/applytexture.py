"""
Apply Texture:

This script will clean up naming schemes for imported .glb objects in blender. 
It will also attempt to find the correct JSON file for mesh / texture data.

@todo: 
	- Glass objects in Village has different keys for mesh_data, add a check for them as well.

@since 0.0.1
"""


import bpy, glob, json, os


# Remove duplicates, if any.
def clean_dupes():
	for obj in bpy.data.objects:
		for slot in obj.material_slots:
			if slot.name[-3:].isnumeric():
				if bpy.data.materials.get(slot.name[:-4]) == None: continue
				real_material = bpy.data.materials[slot.name[:-4]]
				wrong_material = slot.material
				slot.material = real_material
				bpy.data.materials.remove(wrong_material)


# Attempt to apply textures objects in blender scene
def main():

	# Required: Your base path
	# 
	# The base path is the root for TBL/Content.
	# End the path with a slash (/)
	base_path = ''

	# Remove duplicates
	clean_dupes()

	for obj in bpy.data.objects:
		print(f'Processing object: {obj.name}')

		# Clean up naming for objects in blender scene
		obj.name = obj.name.replace('SM_', '').replace('sm_', '').replace('_LOD0', '')

		# JSON Path
		json_path = None

		# Find JSON file path
		for path in glob.glob(base_path + 'TBL/Content/**/*.json', recursive=True):
			if 'SM_' + obj.name + '.json' == os.path.basename(path):
				json_path = path
				break

		# If: Could not fine JSON file, continue to next object
		if json_path == None:
			print('Could not find JSON file. Skipping...')
			continue

		# If: JSON file is found, read it
		with open(json_path) as json_file:
			data = json.load(json_file)

			# Initialize variable for mesh_data
			mesh_data = None

			# If Type is StaticMesh, set that as mesh_data
			for prop in data:
				if prop.get('Type') == 'StaticMesh':
					mesh_data = prop
					break

			# If JSON file is not found, exit loop and continue on
			if mesh_data == None:
				print('Could not find mesh data. Skipping...')
				break

			# Loop through mesh_data & resolve the materials
			for material in mesh_data.get('Properties', {}).get('StaticMaterials'):
				if material.get('ImportedMaterialSlotName') == 'default': continue
				interface = material.get('MaterialInterface', {})
				material_name = interface.get('ObjectName').split(' ')[1]

				print(f'Resolving material instance: {material_name}')
				mat_path = None

				with open(base_path + interface.get('ObjectPath').replace('.0', '.json')) as mi_file:
					mi_json = json.load(mi_file)
					if type(mi_json) == list:
						mic = mi_json[0]

						if mic.get('Type') != 'MaterialInstanceConstant':
							print('Unrecognised material instance. Skipping...')
							continue
						
						param_values = mic.get('Properties', {}).get('TextureParameterValues', {})
						if param_values == None: mat_path = mic.get('Properties', {}).get('PhysMaterial', {}).get('ObjectPath', {})

						if mat_path == None:
							if param_values: 
								for value in param_values:
									if value.get('ParameterInfo').get('Name') in ['L0_Map_C_and_A', 'L0_Map_C', 'Color']:
										mat_path = value.get('ParameterValue', {}).get('ObjectPath', None)

							if mat_path == None: 
								if param_values: 
									for value in param_values:
										object_path = value.get('ParameterValue', {}).get('ObjectPath', None)
										if '_C' in object_path or '_BC' in object_path:
											mat_path = object_path

							if mat_path == None: mat_path = param_values[0]['ParameterValue']['ObjectPath'] if param_values and param_values[0] else None
					
					else: mat_path = mi_json.get('Textures', {}).get('L0_Map_C_and_A', None)

					if mat_path == None:
						print('Could not find L0 Map. Skipping...')
						continue

					mat_path = mat_path.split('.')[0] + '.png'
					print(f'Texture path resolved to: {mat_path}')
					mat_path = base_path + mat_path

				# Apply found textures to blender object
				for material_slot in obj.material_slots:
					if material_name not in material_slot.name: continue
					mat = material_slot.material
					bsdf = mat.node_tree.nodes['Principled BSDF']
					if bsdf.inputs['Base Color'].is_linked:
						mat.node_tree.nodes.remove(bsdf.inputs['Base Color'].links[0].from_node)
					texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
					texture.image = bpy.data.images.load(mat_path)
					mat.node_tree.links.new(bsdf.inputs['Base Color'], texture.outputs['Color'])
					print('Applied texture successfully!')


if __name__ == "__main__":
	main()