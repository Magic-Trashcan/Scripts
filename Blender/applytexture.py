import bpy, glob, json, os

def clean_dupes():
    for obj in bpy.data.objects:
        for slot in obj.material_slots:
            if slot.name[-3:].isnumeric():
                real_material = bpy.data.materials[slot.name[:-4]]
                wrong_material = slot.material
                slot.material = real_material
                bpy.data.materials.remove(wrong_material)

def main():
	base_path = ''

	clean_dupes()

	for obj in bpy.data.objects:
		print(f'Processing object: {obj.name}')
		obj.name = obj.name.replace('SM_', '').replace('sm_', '').replace('_LOD0', '')

		json_path = None

		for path in glob.glob(base_path + 'TBL/Content/**/*.json', recursive=True):
			if 'SM_' + obj.name + '.json' == os.path.basename(path):
				json_path = path
				break

		if json_path == None:
			print('Could not find JSON file. Skipping...')
			continue

		with open(json_path) as json_file:
			data = json.load(json_file)
			mesh_data = None
			for prop in data:
				if prop.get('Type') == 'StaticMesh':
					mesh_data = prop
					break
			if mesh_data == None:
				print('Could not find mesh data. Skipping...')
				break

			for material in mesh_data.get('Properties').get('StaticMaterials'):
				if material.get('ImportedMaterialSlotName') == 'default': continue
				interface = material.get('MaterialInterface')
				material_name = interface.get('ObjectName').split(' ')[1]

				print(f'Resolving material instance: {material_name}')
				mat_path = None

				with open(base_path + interface.get('ObjectPath').replace('.0', '.json')) as mi_file:
					mi_json = json.load(mi_file)
					if type(mi_json) == list:
						print('Using Material Instance Constant. Skipping...')
						continue
					else:
						mat_path = mi_json.get('Textures').get('L0_Map_C_and_A')
						if mat_path == None:
							print('Could not find L0 Map. Skipping...')
							continue
						mat_path = mat_path.split('.')[0] + '.png'
					print(f'Texture path resolved to: {mat_path}')
					mat_path = base_path + mat_path

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