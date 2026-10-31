"""Animate computed vertices only, without titles, legends or overlays."""
import argparse
from pathlib import Path

import numpy as np

from application.tools.export_showcase import cloud_views, save_gif


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cloud', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--yaw', type=float, default=20.)
    parser.add_argument('--pitch', type=float, default=0., help='Inclinaison de la vue pour montrer le sol')
    args = parser.parse_args()
    if not np.isfinite(args.yaw) or not 0 < args.yaw <= 60:
        parser.error('--yaw doit etre compris entre 0 et 60 degres')
    if not np.isfinite(args.pitch) or abs(args.pitch) > 60:
        parser.error('--pitch doit etre compris entre -60 et 60 degres')
    with np.load(args.cloud, allow_pickle=False) as data:
        xyz, rgb = data['xyz'], data['rgb']
    if xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.shape != rgb.shape or len(xyz) < 10 or not np.isfinite(xyz).all():
        parser.error('Nuage invalide')
    angles = args.yaw*np.sin(np.linspace(0, 2*np.pi, 48, endpoint=False))
    frames = list(cloud_views(xyz, rgb, angles, width=960, height=640, pitch_degrees=args.pitch))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_gif(args.output, frames, 90)
    frames[8].save(args.output.with_suffix('.png'))
    print(f'{args.output.name} : {len(frames)} vues, {len(xyz)} points, sans texte')


if __name__ == '__main__':
    main()
