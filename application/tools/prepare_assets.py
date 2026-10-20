"""Download credited public examples. Original video downloads stay in ignored results/."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

import cv2

from application.run import HOME, ROOT, write_image

LICENSE = 'https://www.pexels.com/license/'
SOURCES = [
    ('room.jpg', 'Curtis Adams', 'https://www.pexels.com/photo/wooden-floor-inside-the-house-7601090/',
     'https://images.pexels.com/photos/7601090/pexels-photo-7601090.jpeg?auto=compress&cs=tinysrgb&w=1280'),
    ('warehouse.jpg', 'Erwin Salas', 'https://www.pexels.com/photo/aisle-of-a-huge-store-24862481/',
     'https://images.pexels.com/photos/24862481/pexels-photo-24862481.jpeg?auto=compress&cs=tinysrgb&w=960'),
    ('boxes.jpg', 'Freek Wolsink', 'https://www.pexels.com/photo/industrial-warehouse-with-stacked-cardboard-boxes-34221998/',
     'https://images.pexels.com/photos/34221998/pexels-photo-34221998.jpeg?auto=compress&cs=tinysrgb&w=1280'),
    ('street.jpg', 'Sami Abdullah', 'https://www.pexels.com/photo/cars-in-traffic-on-city-road-16666912/',
     'https://images.pexels.com/photos/16666912/pexels-photo-16666912.jpeg?auto=compress&cs=tinysrgb&w=960'),
    ('dashcam.mp4', 'German Korb', 'https://www.pexels.com/video/dash-cam-footage-in-city-driving-4644521/',
     'https://videos.pexels.com/video-files/4644521/4644521-uhd_2562_1440_30fps.mp4'),
    ('camera-laterale.mp4', 'Teju', 'https://www.pexels.com/video/a-person-is-driving-down-the-road-with-a-car-19713833/',
     'https://videos.pexels.com/video-files/19713833/19713833-hd_1080_1920_30fps.mp4'),
]


def download(url, path):
    if path.exists():
        return
    req = urllib.request.Request(url, headers={'User-Agent': 'MonocularDepthLab/1.0 (public research examples)'})
    partial = path.with_suffix(path.suffix+'.part')
    with urllib.request.urlopen(req, timeout=90) as response, partial.open('wb') as stream:
        while block := response.read(1024*1024):
            stream.write(block)
    partial.replace(path)


def trim_video(source, target, seconds=6):
    cap = cv2.VideoCapture(str(source))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise ValueError('Source video illisible')
    writer = None
    count = 0
    try:
        for _ in range(round(seconds*fps)):
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            ratio = min(1., 768/max(h, w))
            # Even dimensions for portable MP4 encoding.
            width, height = round(w*ratio)//2*2, round(h*ratio)//2*2
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            if writer is None:
                writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
                if not writer.isOpened():
                    raise OSError('Encodeur MP4 indisponible')
                write_image(target.with_suffix('.jpg'), frame)
            writer.write(frame)
            count += 1
    finally:
        cap.release()
        if writer is not None:
            writer.release()
    if count == 0:
        raise ValueError('Video vide')
    return {'frames': count, 'fps': fps, 'duration_seconds': count/fps,
            'transformation': 'Extrait initial, redimensionne, sans audio ni metadonnees de la source.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', action='store_true', help='Preparer aussi les deux extraits video')
    args = parser.parse_args()
    cache = ROOT/'results'/'application'
    cache.mkdir(parents=True, exist_ok=True)
    (HOME/'assets').mkdir(exist_ok=True)
    manifest_path = HOME/'assets'/'SOURCES.json'
    old = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
    records = {record['file']: record for record in old}
    for name, author, page, url in SOURCES:
        target = HOME/'assets'/name
        if target.exists() and name in records and hashlib.sha256(target.read_bytes()).hexdigest() == records[name]['sha256']:
            if not name.endswith('.mp4') or (args.video and target.with_suffix('.jpg').exists()):
                print('Disponible : '+name, flush=True)
                continue
        if name.endswith('.mp4'):
            if not args.video:
                continue
            original = cache/('dashcam-source.mp4' if name == 'dashcam.mp4' else 'traffic-source.mp4')
            download(url, original)
            extra = trim_video(original, target, 6 if name == 'dashcam.mp4' else 4)
        else:
            original = cache/name
            download(url, original)
            photo = cv2.imread(str(original))
            if photo is None:
                raise ValueError('Image telechargee illisible : '+name)
            write_image(target, photo)  # Re-encode to drop original EXIF and metadata.
            extra = {'transformation': 'Redimensionnement CDN puis reencodage JPEG sans EXIF.'}
        records[name] = {'file': name, 'author': author, 'source_page': page,
            'download_url': url, 'license': LICENSE, 'accessed': '2026-10-20',
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), **extra}
        if name.endswith('.mp4'):
            still = target.with_suffix('.jpg')
            records[still.name] = {**records[name], 'file': still.name,
                'sha256': hashlib.sha256(still.read_bytes()).hexdigest(),
                'transformation': 'Premiere image du meme extrait video.'}
        print('Prepare : '+name, flush=True)
    manifest_path.write_text(json.dumps(list(records.values()), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
