"""Single-view metric point clouds, using pretrained models only."""

import argparse
import json
import os
import time
import webbrowser
from pathlib import Path

import cv2
import numpy as np
import torch

from depth import IMAGES, ROOT, load_model, shrink
from pointcloud import camera_intrinsics, unproject, write_ply, write_preview, write_viewer


def reconstruct(path, model, args):
    started = time.perf_counter()
    original = cv2.imread(str(path))
    if original is None:
        raise ValueError(f"Image illisible : {path.name}")
    frame = shrink(original, args.max_side)
    height, width = frame.shape[:2]
    camera = camera_intrinsics((original.shape[1], original.shape[0]), (width, height),
                               args.fov, args.fx, args.fy, args.cx, args.cy)
    with torch.inference_mode():
        depth = model.infer_image(frame, args.size)
    far = args.max_depth if args.max_depth is not None else (20.0 if args.model == "indoor" else 80.0)
    xyz, rgb, pixels, valid = unproject(depth, frame, camera, args.stride, args.min_depth, far, args.edge_threshold)
    if len(xyz) < 10:
        raise ValueError("Trop peu de points. Verifiez les seuils de profondeur et l'image.")
    # The projection check validates the implementation, not real-world depth accuracy.
    reprojection = np.column_stack((camera["fx"] * xyz[:, 0] / xyz[:, 2] + camera["cx"],
                                   camera["fy"] * xyz[:, 1] / xyz[:, 2] + camera["cy"]))
    metadata = {"schema": 1, "model": args.model, "camera": camera, "image_size": [width, height],
                "original_size": [original.shape[1], original.shape[0]], "points": len(xyz),
                "units": "estimated_meters", "axes": "x right, y down, z forward", "single_view": True,
                "depth_limits": [args.min_depth, far], "stride": args.stride, "edge_threshold": args.edge_threshold,
                "input_size": args.size, "max_reprojection_error_pixels": float(np.abs(reprojection - pixels).max()),
                "depth_percentiles_m": [float(x) for x in np.percentile(xyz[:, 2], [5, 50, 95])],
                "seconds": round(time.perf_counter() - started, 3),
                "limitations": ["Unobserved surfaces are absent", "Depth is inferred, not measured",
                                "Distortion is not corrected; supply a rectified image",
                                "Assumed camera intrinsics can deform the geometry"]}
    output = args.output / f"{path.stem}_{args.model}"
    output.parent.mkdir(parents=True, exist_ok=True)
    def artifact(suffix):
        return output.parent / (output.name + suffix)
    np.save(artifact(".npy"), depth)
    np.savez_compressed(artifact(".npz"), xyz=xyz, rgb=rgb, pixels=pixels)
    artifact(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_ply(artifact(".ply"), xyz, rgb)
    write_viewer(artifact(".html"), xyz, rgb, metadata)
    write_preview(artifact(".png"), xyz, rgb)
    # Export only filtered colors for the inspection image; no metadata from source photos is copied.
    lo, hi = np.percentile(depth[np.isfinite(depth)], [2, 98])
    colored = cv2.applyColorMap(np.clip((depth - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    colored[~valid] = 0
    if not cv2.imwrite(str(output.parent / (output.name + "_depth.png")), cv2.hconcat([frame, colored])):
        raise OSError("Cannot save depth preview")
    print(f"{path.name} : {len(xyz):,} points, {metadata['seconds']} s, focale {'estimee' if camera['estimated'] else 'fournie'}", flush=True)
    print(f"Ouvrir : {artifact('.html')}", flush=True)
    return artifact(".html")


def main():
    parser = argparse.ArgumentParser(description="Photo vers nuage de points colore et vue 3D hors ligne")
    parser.add_argument("--input", type=Path, default=ROOT / "inputs")
    parser.add_argument("--output", type=Path, default=ROOT / "results/3d")
    parser.add_argument("--model", choices=["indoor", "outdoor"], default="indoor")
    parser.add_argument("--size", type=int, default=392)
    parser.add_argument("--max-side", type=int, default=960)
    parser.add_argument("--stride", type=int, default=3)
    parser.add_argument("--min-depth", type=float, default=0.1)
    parser.add_argument("--max-depth", type=float)
    parser.add_argument("--edge-threshold", type=float, default=0.1)
    parser.add_argument("--fov", type=float, default=60, help="Champ horizontal estime si la focale n'est pas connue")
    for name in ["fx", "fy", "cx", "cy"]:
        parser.add_argument("--" + name, type=float, help="Parametre en pixels de la photo ORIGINALE")
    parser.add_argument("--open", action="store_true", help="Ouvrir le premier resultat dans le navigateur")
    args = parser.parse_args()
    if args.size < 140 or args.max_side < 140 or args.stride < 1:
        parser.error("Taille minimum : 140 ; stride minimum : 1")
    if not 5 < args.fov < 175 or (args.fx is None) != (args.fy is None):
        parser.error("FOV entre 5 et 175 degres ; fournir fx et fy ensemble")
    limits = [args.min_depth, args.edge_threshold, args.fov] + [v for v in [args.max_depth, args.fx, args.fy, args.cx, args.cy] if v is not None]
    if not np.isfinite(limits).all() or args.min_depth < 0 or args.edge_threshold < 0:
        parser.error("Parametres numeriques invalides")
    if args.max_depth is not None and args.max_depth <= args.min_depth:
        parser.error("max-depth doit depasser min-depth")
    if args.fx is not None and min(args.fx, args.fy) <= 0:
        parser.error("fx et fy doivent etre positifs")
    if not args.input.exists():
        parser.error("Entree introuvable")
    paths = sorted(p for p in args.input.iterdir() if p.suffix.lower() in IMAGES) if args.input.is_dir() else [args.input]
    if not paths or any(p.suffix.lower() not in IMAGES for p in paths):
        parser.error("Choisissez une photo ou un dossier contenant des photos ; videos non prises en charge")
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    model = load_model(args.model)
    first = None
    for path in paths:
        result = reconstruct(path, model, args)
        first = first or result
    if args.open and first:
        webbrowser.open(first.resolve().as_uri())


if __name__ == "__main__":
    main()
