"""Export actual reconstruction and application results as shareable PNGs and GIFs."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from application.run import ROOT

BG = (15, 23, 36)
PANEL = (22, 33, 49)
WHITE = (238, 244, 252)
MUTED = (174, 192, 214)
ACCENT = (72, 211, 190)


def font(size, bold=False):
    name = 'segoeuib.ttf' if bold else 'segoeui.ttf'
    candidates = [Path('C:/Windows/Fonts')/name, Path('/usr/share/fonts/truetype/dejavu')/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def card(title, subtitle, left, right, labels, footer):
    canvas = Image.new('RGB', (1200, 800), BG)
    draw = ImageDraw.Draw(canvas)
    draw.text((38, 24), 'MONOCULAR DEPTH LAB', font=font(20, True), fill=ACCENT)
    draw.text((38, 65), title, font=font(39, True), fill=WHITE)
    draw.text((38, 119), subtitle, font=font(23), fill=MUTED)
    for x, image, label in zip((38, 618), (left, right), labels):
        draw.rounded_rectangle((x, 174, x+544, 661), radius=16, fill=PANEL)
        draw.text((x+16, 187), label, font=font(23, True), fill=WHITE)
        thumb = ImageOps.contain(image.convert('RGB'), (520, 402), Image.Resampling.LANCZOS)
        canvas.paste(thumb, (x+12+(520-thumb.width)//2, 239+(402-thumb.height)//2))
    draw.text((38, 691), footer[0], font=font(23), fill=WHITE)
    draw.text((38, 730), footer[1], font=font(19), fill=MUTED)
    draw.text((38, 767), 'github.com/otmaniamine/monocular-depth-lab', font=font(16), fill=MUTED)
    return canvas


def cloud_views(xyz, rgb, angles, width=1040, height=804, pitch_degrees=0.):
    lo, hi = np.percentile(xyz, [1, 99], axis=0)
    points = xyz-(lo+hi)/2
    distance = max(np.linalg.norm(points, axis=1).max()*2.2, 1.)
    coordinates = []
    pitch = np.deg2rad(pitch_degrees)
    tilt = np.array([[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]])
    for angle in angles:
        yaw = np.deg2rad(angle)
        rotation = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
        q = points @ (tilt @ rotation).T
        z = q[:, 2]+distance
        coordinates.append((q[:, :2]/z[:, None], z))
    # Fixed framing across all views: rotation does not create artificial zoom.
    bounds = np.array([np.percentile(uv, [0, 100], axis=0) for uv, _ in coordinates])
    low, high = bounds[:, 0].min(axis=0), bounds[:, 1].max(axis=0)
    focal = min(width*.94/(high[0]-low[0]), height*.94/(high[1]-low[1]))
    origin = np.array([width, height])/2-focal*(low+high)/2
    for uv, z in coordinates:
        pixels = np.rint(uv*focal+origin).astype(int)
        x, y = pixels.T
        valid = (x >= 1) & (x < width-1) & (y >= 1) & (y < height-1) & (z > 0)
        ids = np.flatnonzero(valid)
        # Stable far-to-near order; nearest vertex wins at a shared pixel.
        order = ids[np.argsort(z[ids], kind='stable')[::-1]]
        raster = np.full((height, width, 3), PANEL, np.uint8)
        for dx, dy in ((-1, 0), (0, -1), (0, 1), (1, 0), (0, 0)):
            raster[y[order]+dy, x[order]+dx] = rgb[order]
        yield Image.fromarray(raster)


def save_gif(path, frames, duration):
    # Shared palette prevents colors from flickering between adjacent frames.
    first = frames[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=first, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=duration,
                    loop=0, optimize=True, disposal=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cloud', type=Path, default=ROOT/'results/3d/showcase/room_indoor.npz')
    parser.add_argument('--output', type=Path, default=ROOT/'docs/showcase')
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    data = np.load(args.cloud, allow_pickle=False)
    xyz, rgb = data['xyz'], data['rgb']
    if xyz.shape != rgb.shape or not np.isfinite(xyz).all():
        raise ValueError('Nuage invalide')
    photo = Image.open(ROOT/'application/assets/room.jpg').convert('RGB')
    angles = 23*np.sin(np.linspace(0, 2*np.pi, 48, endpoint=False))
    frames = []
    count = f'{len(xyz):,}'.replace(',', ' ')
    for index, view in enumerate(cloud_views(xyz, rgb, angles, width=960, height=640)):
        image = card('Une photo. Une représentation 3D.',
            'Modèle préentraîné · Calcul local sur CPU · Sans entraînement ajouté', photo, view,
            ('Photo réelle', 'Nuage de points · vue mobile'),
            (f'{count} points colorés, calculés à partir de la profondeur estimée.',
             'Photo : Curtis Adams / Pexels · Surfaces visibles uniquement · Focale supposée'))
        if index == 8:
            image.save(output/'01-reconstruction-3d.png')
        # Animation contains geometry only: titles and credits stay in static cards/docs.
        frames.append(view)
    save_gif(output/'reconstruction-3d.gif', frames, 90)
    Image.open(output/'01-reconstruction-3d.png').save(ROOT/'docs/examples/reconstruction-3d.png')
    applications = [
        ('05_industrie_passage', 'boxes.jpg', '02-application-industrie.png',
         'Industrie : où faut-il vérifier ?', 'Surfaces candidates au-dessus du sol estimé',
         'Photo réelle', 'Surfaces à examiner',
         'Une aide à la revue visuelle des passages en entrepôt.',
         'Photo : Freek Wolsink / Pexels · Résultat expérimental, à confirmer sur place'),
        ('03_traitement_image', 'room.jpg', '03-traitement-image.png',
         'La profondeur au service de la photo', 'Mise au point choisie sur le fauteuil · Flou progressif',
         'Avant', 'Après : flou selon la profondeur',
         'Mettre en valeur un sujet sans tracer tout son contour à la main.',
         'Photo : Curtis Adams / Pexels · Retouche calculée, contours approximatifs'),
        ('04_entreprise_amenagement', 'room.jpg', '04-application-entreprise.png',
         'Prévisualiser avant de mesurer', 'Projection d’un volume virtuel avec test d’occlusion',
         'Photo du logement', 'Gabarit virtuel illustratif',
         'Discuter un emplacement avant une visite ou un devis.',
         'Photo : Curtis Adams / Pexels · Dimensions supposées, mesure réelle nécessaire'),
    ]
    for folder, source, name, title, subtitle, left, right, line, credit in applications:
        original = Image.open(ROOT/'application/assets'/source)
        result = Image.open(ROOT/'results/application'/folder/'vue_001_resultat.jpg')
        card(title, subtitle, original, result, (left, right), (line, credit)).save(output/name)
    video = cv2.VideoCapture(str(ROOT/'application/01_navigation_routiere/video/video_annotee.webm'))
    source_video = cv2.VideoCapture(str(ROOT/'application/assets/dashcam.mp4'))
    video_reports = json.loads((ROOT/'application/01_navigation_routiere/video/rapport.json').read_text(encoding='utf-8'))
    fps = video.get(cv2.CAP_PROP_FPS)
    timeline = []
    try:
        while True:
            ok, bgr = video.read()
            if not ok:
                break
            source_video.set(cv2.CAP_PROP_POS_FRAMES, video_reports[len(timeline)]['frame_index'])
            source_ok, source_bgr = source_video.read()
            if not source_ok:
                raise ValueError('Image source video indisponible')
            original_video_frame = Image.fromarray(cv2.cvtColor(source_bgr, cv2.COLOR_BGR2RGB))
            image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            timeline.append(card('Une caméra, des zones à examiner',
                'Analyse vidéo hors ligne · Profondeur monoculaire estimée', original_video_frame, image,
                ('Vidéo réelle', 'Secteurs surveillés'),
                ('Vigilance et alertes à confirmer : aucune commande du véhicule.',
                 'Vidéo : German Korb / Pexels · Surfaces géométriques, pas reconnaissance d’objets'))
                .resize((960, 640), Image.Resampling.LANCZOS))
    finally:
        video.release()
        source_video.release()
    if timeline:
        save_gif(output/'application-video.gif', timeline, round(1000/fps))
    metadata = json.loads(args.cloud.with_suffix('.json').read_text(encoding='utf-8'))
    metadata.pop('seconds', None)
    metadata['source'] = 'application/assets/room.jpg'
    metadata['gif'] = {'frames': len(frames), 'duration_ms': 90, 'yaw_degrees': [-23, 23],
                       'description': 'Camera orbit of computed points; no hidden geometry generated.'}
    (output/'reconstruction.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Visuels exportes : {output.name} | {len(xyz)} points | {len(frames)} vues GIF')


if __name__ == '__main__':
    main()
