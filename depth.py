"""Inference locale avec les poids officiels Depth Anything V2 Small."""

import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
MIDAS = ROOT / "midas"
MODELS = {
    "relative": (SOURCE, SOURCE / "checkpoints/depth_anything_v2_vits.pth", None),
    "indoor": (SOURCE / "metric_depth", SOURCE / "metric_depth/checkpoints/depth_anything_v2_metric_hypersim_vits.pth", 20),
    "outdoor": (SOURCE / "metric_depth", SOURCE / "metric_depth/checkpoints/depth_anything_v2_metric_vkitti_vits.pth", 80),
    "hybrid": (MIDAS, MIDAS / "weights/dpt_hybrid_384.pt", None),
    "large": (MIDAS, MIDAS / "weights/dpt_large_384.pt", None),
}
IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
VIDEOS = {".mp4", ".avi", ".mov", ".mkv", ".m4v"}


def load_model(kind):
    source_dir, checkpoint, max_depth = MODELS[kind]
    if not checkpoint.is_file() or checkpoint.stat().st_size < 1_000_000:
        raise FileNotFoundError(f"Poids du modele absents ou incomplets : {checkpoint}")
    if kind in {"hybrid", "large"}:
        sys.path.insert(0, str(MIDAS))
        from midas.model_loader import load_model as load_midas

        model_type = "dpt_hybrid_384" if kind == "hybrid" else "dpt_large_384"
        model, transform, _, _ = load_midas(torch.device("cpu"), str(checkpoint), model_type, optimize=False)
        return MiDaSPredictor(model, transform)
    sys.path.insert(0, str(source_dir))
    from depth_anything_v2.dpt import DepthAnythingV2

    config = {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]}
    if max_depth is not None:
        config["max_depth"] = max_depth
    model = DepthAnythingV2(**config)
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    return model.eval()


class MiDaSPredictor:
    def __init__(self, model, transform):
        self.model = model
        self.transform = transform

    def infer_image(self, frame, _size):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) / 255.0
        prepared = self.transform({"image": rgb})["image"]
        sample = torch.from_numpy(prepared).unsqueeze(0)
        prediction = self.model(sample)
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1), size=frame.shape[:2], mode="bicubic", align_corners=False
        )[0, 0]
        return prediction.numpy()


def shrink(frame, max_side):
    height, width = frame.shape[:2]
    scale = min(1.0, max_side / max(height, width))
    if scale == 1.0:
        return frame
    return cv2.resize(frame, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def render(frame, model, size):
    depth = model.infer_image(frame, size)
    lo, hi = np.percentile(depth, [2, 98])
    normalized = np.clip((depth - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    colored = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)
    return depth, cv2.hconcat([frame, colored])


def process_image(path, output_dir, model, size, max_side, metric):
    frame = cv2.imread(str(path))
    if frame is None:
        raise ValueError(f"Image illisible : {path}")
    frame = shrink(frame, max_side)
    depth, preview = render(frame, model, size)
    out = output_dir / f"{path.stem}_depth.png"
    if not cv2.imwrite(str(out), preview):
        raise OSError(f"Ecriture impossible : {out}")
    if metric:
        np.save(output_dir / f"{path.stem}_meters.npy", depth)
    print(f"Image creee : {out}", flush=True)


def process_video(path, output_dir, model, size, max_side, max_frames):
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Video illisible : {path}")
    writer = None
    out = output_dir / f"{path.stem}_depth.mp4"
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not np.isfinite(fps) or fps <= 0:
        fps = 25.0
    count = 0
    try:
        while max_frames is None or count < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            frame = shrink(frame, max_side)
            _, preview = render(frame, model, size)
            if writer is None:
                height, width = preview.shape[:2]
                writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
                if not writer.isOpened():
                    raise OSError(f"Ecriture video impossible : {out}")
            writer.write(preview)
            count += 1
            if count % 30 == 0:
                print(f"{count} images video traitees", flush=True)
    finally:
        capture.release()
        if writer is not None:
            writer.release()
    if count == 0:
        raise ValueError(f"Aucune image dans la video : {path}")
    print(f"Video creee ({count} images) : {out}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Cartes de profondeur locales, sans entrainement")
    parser.add_argument("--input", required=True, type=Path, help="Photo, video ou dossier")
    parser.add_argument("--model", choices=MODELS, default="relative")
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    parser.add_argument("--size", type=int, default=392, help="Taille d'inference (defaut : 392)")
    parser.add_argument("--max-side", type=int, default=1280, help="Plus grand cote de sortie")
    parser.add_argument("--max-frames", type=int, help="Limiter une video pour un essai rapide")
    args = parser.parse_args()
    if args.size < 140 or args.max_side < 140:
        parser.error("--size et --max-side doivent etre >= 140")
    if not args.input.exists():
        parser.error(f"Fichier introuvable : {args.input}")
    paths = sorted(p for p in args.input.iterdir() if p.suffix.lower() in IMAGES | VIDEOS) if args.input.is_dir() else [args.input]
    if not paths:
        parser.error("Aucune photo ou video reconnue dans le dossier")
    output_dir = args.output.resolve() / args.model
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    model = load_model(args.model)
    with torch.inference_mode():
        for path in paths:
            extension = path.suffix.lower()
            if extension in IMAGES:
                process_image(path, output_dir, model, args.size, args.max_side, args.model in {"indoor", "outdoor"})
            elif extension in VIDEOS:
                process_video(path, output_dir, model, args.size, args.max_side, args.max_frames)
            else:
                print(f"Format ignore : {path}")


if __name__ == "__main__":
    main()
