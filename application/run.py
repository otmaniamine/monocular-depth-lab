"""VS Code / PowerShell: python -m application.run --demo all."""
import argparse
import csv
import gc
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import cv2
import numpy as np

from application.geometry import (TemporalReview, analyse_obstacles, depth_focus,
                                  rectangle, render_cuboid)
from pointcloud import camera_intrinsics

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'application'
PROFILES = {
    'route': dict(folder='01_navigation_routiere', model='outdoor', image='street.jpg', fov=45,
        title='Perception routiere monoculaire', roi=(.05, .48, .95, .98), seed=(.36, .78, .64, .96),
        tolerance=.15, min_height=.25, max_height=3., max_depth=79., watch_distance=25., alert_distance=8.,
        action='Dans le simulateur : suspendre la progression et demander une confirmation humaine.'),
    'robot': dict(folder='02_robot_aspirateur', model='indoor', image='room.jpg', fov=80,
        title='Robot aspirateur : surveillance du sol', roi=(.05, .45, .95, .98), seed=(.25, .79, .75, .97),
        tolerance=.06, min_height=.08, max_height=1.5, max_depth=19., watch_distance=6., alert_distance=2.,
        action='Dans le simulateur : mettre le robot en pause et confirmer le contournement avec une autre vue.'),
    'photo': dict(folder='03_traitement_image', model='indoor', image='room.jpg', fov=80,
        title='Retouche : flou pilote par la profondeur'),
    'entreprise': dict(folder='04_entreprise_amenagement', model='indoor', image='room.jpg', fov=80,
        title='Entreprise : previsualiser un gabarit de meuble'),
    'industrie': dict(folder='05_industrie_passage', model='indoor', image='boxes.jpg', fov=65,
        title='Industrie : revue visuelle du passage', roi=(.15, .35, .90, .98), seed=(.19, .77, .50, .96),
        tolerance=.08, min_height=.15, max_height=3., max_depth=19., watch_distance=8., alert_distance=5.,
        action='Demander une inspection du passage et deplacer les objets confirmes genants avant circulation.'),
}


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def write_image(path, image):
    if not cv2.imwrite(str(path), image):
        raise OSError(f'Ecriture impossible : {path.name}')


def heatmap(depth):
    valid = np.isfinite(depth) & (depth > 0)
    if not valid.any():
        return np.zeros((*depth.shape, 3), np.uint8)
    low, high = np.percentile(depth[valid], [2, 98])
    scale = np.clip((np.where(valid, depth, low)-low)/max(high-low, .001)*255, 0, 255).astype(np.uint8)
    result = cv2.applyColorMap(scale, cv2.COLORMAP_TURBO)
    result[~valid] = 0
    return result


def dashboard(images, titles, heading, lines):
    """Fixed-size comparison, including portrait source photos without stretching."""
    width, height, gap = 360, 440, 12
    canvas = np.full((height+185, width*len(images)+gap*(len(images)+1), 3), (26, 23, 19), np.uint8)
    cv2.putText(canvas, heading, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, .67, (245, 235, 220), 1, cv2.LINE_AA)
    for i, (im, title) in enumerate(zip(images, titles)):
        left = gap+i*(width+gap)
        cv2.putText(canvas, title, (left, 67), cv2.FONT_HERSHEY_SIMPLEX, .48, (210, 205, 195), 1, cv2.LINE_AA)
        ih, iw = im.shape[:2]
        ratio = min(width/iw, height/ih)
        resized = cv2.resize(im, (round(iw*ratio), round(ih*ratio)), interpolation=cv2.INTER_AREA)
        rh, rw = resized.shape[:2]
        x, y = left+(width-rw)//2, 82+(height-rh)//2
        canvas[y:y+rh, x:x+rw] = resized
    for i, line in enumerate(lines[:3]):
        cv2.putText(canvas, line[:135], (16, height+111+i*22), cv2.FONT_HERSHEY_SIMPLEX, .46,
                    (215, 220, 225), 1, cv2.LINE_AA)
    return canvas


def annotate(frame, mask, report, profile):
    result = frame.copy()
    colored = result.copy()
    colored[mask.astype(bool)] = (50, 60, 235)
    result = cv2.addWeighted(result, .48, colored, .52, 0)
    h, w = mask.shape
    x0, y0, x1, y1 = rectangle(mask.shape, profile['roi'])
    cv2.rectangle(result, (x0, y0), (x1-1, y1-1), (235, 190, 50), 2)
    for index in (1, 2):
        x = x0+(x1-x0)*index//3
        cv2.line(result, (x, y0), (x, y1-1), (235, 190, 50), 1)
    for c in report['candidates']:
        x, y, bw, bh = c['box_xywh']
        cv2.rectangle(result, (x, y), (x+bw-1, y+bh-1), (45, 70, 245), 2)
    if report.get('floor'):
        sx0, sy0, sx1, sy1 = rectangle(mask.shape, profile['seed'])
        cv2.rectangle(result, (sx0, sy0), (sx1-1, sy1-1), (100, 220, 100), 1)
    cv2.rectangle(result, (0, 0), (w, 31), (20, 20, 20), -1)
    cv2.putText(result, report['status'], (8, 22), cv2.FONT_HERSHEY_SIMPLEX, .52,
                (60, 170, 255) if report['status'] == 'ABSTENTION' else (240, 240, 240), 1, cv2.LINE_AA)
    return result


def process(frame, depth, app, args, source='entree_utilisateur'):
    profile = PROFILES[app]
    h, w = depth.shape
    camera = camera_intrinsics((w, h), (w, h), fov=args.fov or profile['fov'])
    report = {'application': app, 'source': source, 'model': profile['model'], 'algorithm_version': 'application-v1',
        'image_size': [w, h], 'camera': camera,
        'limits': ['Profondeur monoculaire estimee et focale supposee ; echelle non validee.',
                   'Demonstration hors ligne, aucune commande de vehicule ou de machine.',
                   'Surfaces visibles uniquement ; erreurs possibles sur verre, reflets et objets fins.']}
    if app in ('route', 'robot', 'industrie'):
        p = dict(profile)
        if args.seed:
            p['seed'] = tuple(args.seed)
        if args.roi:
            p['roi'] = tuple(args.roi)
        analysis, mask = analyse_obstacles(depth, camera, p, camera_ok=not args.camera_lateral)
        report.update(analysis)
        report['parameters'] = {key: p[key] for key in ('roi', 'seed', 'tolerance', 'min_height',
            'max_height', 'watch_distance', 'alert_distance')}
        report['limits'] += ['La zone verte doit contenir un sol approximativement plan, choisi par l utilisateur.',
                             'Le masque est geometrique : il ne reconnait pas voitures, personnes ou cartons.',
                             'A_CONFIRMER ne signifie jamais passage libre ; marches et trous non detectes.']
        result = annotate(frame, mask, analysis, p)
        mask = mask*255
        lines = [analysis['status']+' | '+analysis.get('reason', ''), analysis['action'],
                 'Rouge : surfaces candidates | Cadre bleu : zone | Cadre vert : hypothese de sol']
    elif app == 'photo':
        focus = tuple(args.focus)
        result, amount, target = depth_focus(frame, depth, focus)
        report.update(status='EFFET_PRODUIT', focus_normalized=list(focus), focus_depth_estimated_m=target,
                      action='Ajuster --focus X Y pour choisir le sujet a conserver net.',
                      limits=report['limits']+['Flou artistique approximatif ; halos possibles aux contours.'])
        mask = (amount*255).astype(np.uint8)
        marked = result.copy()
        cv2.drawMarker(marked, (int(focus[0]*(w-1)), int(focus[1]*(h-1))), (50, 210, 255),
                       cv2.MARKER_CROSS, 20, 2)
        lines = ['EFFET PRODUIT | Mise au point choisie par un clic normalise.',
                 'La profondeur commande progressivement le flou du fond et du premier plan.',
                 'Usage : mise en valeur de photos produit, portraits et contenus publicitaires.']
    else:
        result, visible, volume = render_cuboid(frame, depth, camera, tuple(args.anchor), tuple(args.dimensions))
        mask = visible.astype(np.uint8)*255
        report.update(status='GABARIT_PRODUIT', volume=volume,
            action='Comparer visuellement cet emplacement puis mesurer et calibrer avant tout achat.',
            limits=report['limits']+['Gabarit cubique illustratif, pas un modele catalogue ni une preuve de dimensions.',
              'Ancrage manuel sur le sol, volume aligne aux axes camera ; camera supposee approximativement horizontale.'])
        lines = ['GABARIT PRODUIT | Volume virtuel projete avec test d occlusion.',
                 'Usage entreprise : discuter une implantation avant une visite ou un devis.',
                 'Ancrage manuel, focale et dimensions supposees : mesure sur place necessaire.']
    panels_result = marked if app == 'photo' else result
    comparison = dashboard([frame, heatmap(depth), panels_result],
                           ['Photo reelle', 'Profondeur estimee (froid=proche)', 'Application / resultat'],
                           profile['title'], lines)
    return report, result, mask, comparison


def write_report(output, reports):
    save_json(output/'rapport.json', reports)
    first = reports[0]
    body = ['# '+PROFILES[first['application']]['title'], '',
            'Résultats calculés sur des médias réels. Les valeurs sont des estimations du modèle, sans vérité terrain.', '']
    for i, r in enumerate(reports):
        body += [f"## Vue {i+1} — {r['status']}", '', r.get('reason', ''), '', '**Action proposée :** '+r['action'], '']
        if r.get('candidates') is not None:
            body += [f"{len(r['candidates'])} composante(s) géométrique(s) retenue(s). Le nombre ne représente pas un comptage d'objets.", '']
        if 'time_seconds' in r:
            body += [f"Instant de la vidéo source : {r['time_seconds']:.3f} s ; état temporel : {r['temporal_status']}.", '']
    body += ['## Limites', '']+['- '+s for s in first['limits']]
    (output/'RAPPORT.md').write_text('\n'.join(body)+'\n', encoding='utf-8')
    images = [output/f'vue_{i+1:03d}_comparaison.jpg' for i in range(len(reports))]
    cards = ''.join(f'<figure><img src="{html.escape(p.name)}"><figcaption>{html.escape(p.stem)}</figcaption></figure>' for p in images)
    entries = ''.join('<p><b>'+html.escape(r['status'])+'</b> — '+html.escape(r['action'])+'</p>' for r in reports)
    video = ('<video controls muted playsinline style="max-width:100%">'
             '<source src="video_annotee.webm" type="video/webm">'
             '<source src="video_annotee.mp4" type="video/mp4"></video>') if 'time_seconds' in first else ''
    page = ('<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>Applications de la profondeur</title><style>body{font:17px system-ui;background:#151a23;color:#edf0f7;'
            'max-width:1200px;margin:32px auto;padding:16px}img{width:100%}figure{margin:20px 0}a{color:#8ccaff}</style>'
            '<h1>'+html.escape(PROFILES[first['application']]['title'])+'</h1>'+video+entries+cards+
            '<p>Profondeur estimée, focale supposée. Démonstration hors ligne.</p><p><a href="RAPPORT.md">Rapport</a> · '
            '<a href="rapport.json">Données</a></p></html>')
    (output/'index.html').write_text(page, encoding='utf-8')


def export_browser_video(path):
    """MP4V is useful for desktop players; VP8/WebM also works in Chromium."""
    capture = cv2.VideoCapture(str(path))
    writer = None
    try:
        if not capture.isOpened():
            raise ValueError('Video annotee illisible')
        fps = capture.get(cv2.CAP_PROP_FPS)
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if writer is None:
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(str(path.with_suffix('.webm')), cv2.VideoWriter_fourcc(*'VP80'), fps, (w, h))
                if not writer.isOpened():
                    raise OSError('Encodeur WebM indisponible : utiliser le fichier MP4 dans un lecteur compatible.')
            writer.write(frame)
        if writer is None:
            raise ValueError('Video annotee vide')
    finally:
        capture.release()
        if writer is not None:
            writer.release()


def run(args):
    import torch
    from depth import IMAGES, VIDEOS, load_model, shrink
    profile = PROFILES[args.app]
    path = args.input or HOME/'assets'/profile['image']
    output = args.output or ROOT/'results'/'application'/profile['folder']
    output.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        raise ValueError('Entree introuvable. Utiliser --input photo.jpg ou --demo all.')
    video = path.suffix.lower() in VIDEOS
    if video and args.app not in ('route', 'robot', 'industrie'):
        raise ValueError('Video disponible pour route, robot et industrie.')
    if not video and path.suffix.lower() not in IMAGES:
        raise ValueError('Format non pris en charge.')
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    model = load_model(profile['model'])
    reports = []
    temporal = TemporalReview()
    cap = cv2.VideoCapture(str(path)) if video else None
    writer = None
    try:
        if video and not cap.isOpened():
            raise ValueError('Video illisible')
        fps = cap.get(cv2.CAP_PROP_FPS) if video else 1.
        if not np.isfinite(fps) or fps <= 0:
            raise ValueError('Cadence video inconnue ; transcoder avec une cadence definie.')
        with torch.inference_mode():
            index = 0
            while len(reports) < (args.max_frames if video else 1):
                if video:
                    ok, frame = cap.read()
                    if not ok:
                        break
                    if index % args.every:
                        index += 1
                        continue
                else:
                    frame = cv2.imread(str(path))
                    if frame is None:
                        raise ValueError('Photo illisible')
                frame = shrink(frame, args.max_side)
                start = time.perf_counter()
                depth = model.infer_image(frame, args.size)
                source = path.name if path.resolve().parent == HOME/'assets' else 'entree_utilisateur'
                report, result, mask, comparison = process(frame, depth, args.app, args, source)
                report['processing_seconds'] = round(time.perf_counter()-start, 3)
                if video:
                    report.update(frame_index=index, time_seconds=index/fps, source_fps=fps,
                                  temporal_status=temporal.update(report['status']))
                    cv2.putText(result, f't={index/fps:.2f}s | {report["temporal_status"]}',
                                (8, result.shape[0]-12), cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 240, 60), 1)
                    if writer is None:
                        writer = cv2.VideoWriter(str(output/'video_annotee.mp4'), cv2.VideoWriter_fourcc(*'mp4v'),
                                                fps/args.every, (result.shape[1], result.shape[0]))
                        if not writer.isOpened():
                            raise OSError('Encodeur video indisponible')
                    writer.write(result)
                prefix = f'vue_{len(reports)+1:03d}'
                np.save(output/f'{prefix}_depth.npy', depth)
                write_image(output/f'{prefix}_resultat.jpg', result)
                write_image(output/f'{prefix}_masque.png', mask)
                write_image(output/f'{prefix}_comparaison.jpg', comparison)
                reports.append(report)
                print(f'{args.app} | vue {len(reports)} | {report["status"]} | {report["processing_seconds"]} s', flush=True)
                index += 1
        if not reports:
            raise ValueError('Aucune image exploitable')
        if video:
            with (output/'chronologie.csv').open('w', newline='', encoding='utf-8') as stream:
                table = csv.DictWriter(stream, fieldnames=['frame_index', 'time_seconds', 'status', 'temporal_status', 'action'])
                table.writeheader()
                table.writerows({key: r[key] for key in table.fieldnames} for r in reports)
    finally:
        if cap is not None:
            cap.release()
        if writer is not None:
            writer.release()
        del model
        gc.collect()
    if video:
        export_browser_video(output/'video_annotee.mp4')
    write_report(output, reports)
    print('Rapport : '+str(output/'index.html'), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', choices=PROFILES, default='robot')
    parser.add_argument('--demo', choices=['all']+list(PROFILES))
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--size', type=int, default=392)
    parser.add_argument('--max-side', type=int, default=768)
    parser.add_argument('--max-frames', type=int, default=12)
    parser.add_argument('--every', type=int, default=10, help='Video : une image sur N')
    parser.add_argument('--fov', type=float, help='Champ horizontal suppose, en degres')
    parser.add_argument('--seed', type=float, nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'), help='Zone normalisee de sol plan')
    parser.add_argument('--roi', type=float, nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'), help='Zone normalisee a surveiller')
    parser.add_argument('--camera-lateral', action='store_true', help='Camera inadaptee : abstention explicite')
    parser.add_argument('--focus', type=float, nargs=2, default=[.35, .66], metavar=('X', 'Y'))
    parser.add_argument('--anchor', type=float, nargs=2, default=[.72, .87], metavar=('X', 'Y'))
    parser.add_argument('--dimensions', type=float, nargs=3, default=[.8, .7, .55], metavar=('LARGEUR', 'HAUTEUR', 'PROFONDEUR'))
    args = parser.parse_args()
    if args.size < 140 or args.max_side < 140 or args.every < 1 or args.max_frames < 1:
        parser.error('Taille >= 140 ; cadence et nombre de vues >= 1 requis.')
    if args.fov is not None and not 5 < args.fov < 175:
        parser.error('Champ horizontal compris entre 5 et 175 degres requis.')
    for key in ('focus', 'anchor', 'seed', 'roi'):
        value = getattr(args, key)
        if value is not None and (not np.isfinite(value).all() or any(x < 0 or x > 1 for x in value)):
            parser.error(f'--{key} : coordonnees normalisees dans [0, 1] requises.')
        if value is not None and len(value) == 4 and not (value[0] < value[2] and value[1] < value[3]):
            parser.error(f'--{key} : rectangle vide ou inverse.')
    if not np.isfinite(args.dimensions).all() or min(args.dimensions) <= 0:
        parser.error('Dimensions positives et finies requises.')
    if args.demo == 'all':
        if args.input or args.output:
            parser.error('--demo all utilise les exemples et sorties par defaut ; lancer chaque application pour personnaliser.')
        for app in PROFILES:
            subprocess.run([sys.executable, '-m', 'application.run', '--demo', app,
                            '--size', str(args.size), '--max-side', str(args.max_side)], cwd=ROOT, check=True)
        return
    if args.demo:
        args.app = args.demo
    run(args)


if __name__ == '__main__':
    main()
