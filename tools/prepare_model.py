"""Run inside Blender with --background --python-exit-code 1 --python ... --."""
import argparse
import json
from pathlib import Path
import sys

import bpy

parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--max-triangles", type=int, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
if args.source.resolve() == args.output.resolve():
    parser.error("Source and derivative must be different files.")
if args.output.suffix.lower() not in {".fbx", ".glb"}:
    parser.error("Output must be FBX or GLB.")
if args.source.suffix.lower() == ".blend":
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()), use_scripts=False)
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if args.source.suffix.lower() == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(args.source.resolve()))
    elif args.source.suffix.lower() in {".gltf", ".glb"}:
        bpy.ops.import_scene.gltf(filepath=str(args.source.resolve()))
    else:
        parser.error("Source must be BLEND, FBX, GLTF, or GLB.")

meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
triangles = 0
graph = bpy.context.evaluated_depsgraph_get()
for obj in meshes:
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    triangles += len(mesh.loop_triangles)
    evaluated.to_mesh_clear()
if not meshes or triangles > args.max_triangles:
    raise ValueError(f"Model has {len(meshes)} meshes and {triangles} triangles.")

args.output.parent.mkdir(parents=True, exist_ok=True)
if args.output.suffix.lower() == ".fbx":
    bpy.ops.export_scene.fbx(filepath=str(args.output.resolve()),
                             object_types={"ARMATURE", "EMPTY", "MESH"}, add_leaf_bones=False)
else:
    bpy.ops.export_scene.gltf(filepath=str(args.output.resolve()), export_format="GLB",
                              export_cameras=False, export_lights=False)
args.output.with_suffix(args.output.suffix + ".json").write_text(
    json.dumps({"mesh_count": len(meshes), "evaluated_triangles": triangles}, indent=2) + "\n",
    encoding="utf-8",
)
