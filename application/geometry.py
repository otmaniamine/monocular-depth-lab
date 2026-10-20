"""Geometric experiments. All lengths inherit monocular depth and camera errors."""
import cv2
import numpy as np


def xyz_map(depth, camera):
    y, x = np.indices(depth.shape)
    return np.stack(((x-camera['cx'])*depth/camera['fx'],
                     (y-camera['cy'])*depth/camera['fy'], depth), axis=-1)


def rectangle(shape, bounds):
    h, w = shape
    x0, y0, x1, y1 = bounds
    return (int(x0*w), int(y0*h), min(w, int(x1*w)), min(h, int(y1*h)))


def floor_plane(depth, camera, seed=(.32, .72, .68, .97), tolerance=.07):
    """RANSAC on a manually chosen floor seed. Reject wall-like or unsupported fits."""
    xyz = xyz_map(depth, camera)
    x0, y0, x1, y1 = rectangle(depth.shape, seed)
    patch = xyz[y0:y1:3, x0:x1:3].reshape(-1, 3)
    patch = patch[np.isfinite(patch).all(axis=1) & (patch[:, 2] > .1)]
    if len(patch) < 80:
        return None
    rng = np.random.default_rng(42)
    if len(patch) > 1800:
        patch = patch[rng.choice(len(patch), 1800, replace=False)]
    best = None
    best_count = 0
    for _ in range(180):
        a, b, c = patch[rng.choice(len(patch), 3, replace=False)]
        normal = np.cross(b-a, c-a)
        norm = np.linalg.norm(normal)
        if norm < 1e-7:
            continue
        normal /= norm
        if normal[1] > 0:
            normal = -normal
        offset = -normal @ a
        if -normal[1] < .65 or not .08 < offset < 5:
            continue
        keep = np.abs(patch @ normal + offset) < tolerance
        count = int(keep.sum())
        if count > best_count:
            best, best_count = keep, count
    if best is None or best_count < max(80, len(patch)*.55):
        return None
    support = patch[best]
    center = support.mean(axis=0)
    _, singular, vh = np.linalg.svd(support-center, full_matrices=False)
    normal = vh[-1]
    if normal[1] > 0:
        normal = -normal
    offset = -normal @ center
    residual = np.abs(support @ normal + offset)
    # Floor must have two-dimensional extent, and retain a plausible orientation.
    if -normal[1] < .65 or not .08 < offset < 5 or singular[1] < .12:
        return None
    if np.quantile(residual, .90) > tolerance:
        return None
    return {'normal': normal.tolist(), 'offset': float(offset),
            'seed_inlier_fraction': best_count / len(patch),
            'residual_p90_estimated_m': float(np.quantile(residual, .90)),
            'seed': list(seed), 'tolerance_estimated_m': tolerance}


def analyse_obstacles(depth, camera, profile, camera_ok=True):
    h, w = depth.shape
    roi = np.zeros((h, w), bool)
    x0, y0, x1, y1 = rectangle(depth.shape, profile['roi'])
    roi[y0:y1, x0:x1] = True
    valid = np.isfinite(depth) & (depth > .1) & (depth < profile['max_depth'])
    coverage = float(valid[roi].mean()) if roi.any() else 0.
    report = {'status': 'ABSTENTION', 'valid_fraction_in_roi': coverage,
              'roi': list(profile['roi']), 'candidates': [], 'zones': [],
              'action': 'Verifier la camera et la profondeur avant toute decision.',
              'interpretation': 'Candidats geometriques, sans reconnaissance de classe ni preuve de passage libre.'}
    empty = np.zeros((h, w), np.uint8)
    if not camera_ok:
        report['reason'] = 'Camera declaree laterale ou inadaptee : vue frontale requise.'
        return report, empty
    if coverage < .8:
        report['reason'] = 'Profondeur insuffisante dans la zone de surveillance.'
        return report, empty
    plane = floor_plane(depth, camera, profile['seed'], profile['tolerance'])
    report['floor'] = plane
    if plane is None:
        report['reason'] = 'Sol non valide : changer la zone de sol ou calibrer la camera.'
        return report, empty
    height = xyz_map(depth, camera) @ np.array(plane['normal']) + plane['offset']
    mask = (roi & valid & (height > profile['min_height']) &
            (height < profile['max_height']) & (depth < profile['watch_distance'])).astype(np.uint8)
    # Opening removes isolated prediction noise, but thin obstacles can disappear.
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    clean = np.zeros_like(mask)
    min_area = max(25, int(roi.sum()*.002))
    for label in range(1, count):
        x, y, bw, bh, area = map(int, stats[label])
        if area < min_area:
            continue
        selected = labels == label
        clean[selected] = 1
        z = depth[selected]
        report['candidates'].append({'box_xywh': [x, y, bw, bh], 'pixels': area,
            'depth_p10_estimated_m': float(np.quantile(z, .1)),
            'depth_median_estimated_m': float(np.median(z))})
    for index, name in enumerate(('gauche', 'centre', 'droite')):
        left = x0+(x1-x0)*index//3
        right = x0+(x1-x0)*(index+1)//3
        selected = clean[y0:y1, left:right].astype(bool)
        values = depth[y0:y1, left:right][selected]
        report['zones'].append({'zone': name, 'candidate_pixels': int(selected.sum()),
            'depth_p10_estimated_m': float(np.quantile(values, .1)) if len(values) else None})
    near = any(c['depth_p10_estimated_m'] < profile['alert_distance'] for c in report['candidates'])
    if near:
        report.update(status='ALERTE_SIMULEE', reason='Surface saillante proche dans la zone choisie.',
                      action=profile['action'])
    elif report['candidates']:
        report.update(status='VIGILANCE', reason='Surfaces saillantes dans la zone surveillee.',
                      action='Examiner les zones annotees et confirmer avec une autre vue.')
    else:
        report.update(status='A_CONFIRMER', reason='Aucun candidat dans ces seuils ; absence non garantie.',
                      action='Verifier le passage sur place ou par un autre capteur avant de poursuivre.')
    return report, clean


def depth_focus(frame, depth, focus=(.35, .66), strength=17):
    h, w = depth.shape
    u, v = int(focus[0]*(w-1)), int(focus[1]*(h-1))
    patch = depth[max(0, v-5):v+6, max(0, u-5):u+6]
    valid = np.isfinite(patch) & (patch > 0)
    if not valid.any():
        raise ValueError('Profondeur invalide au point de mise au point')
    target = float(np.median(patch[valid]))
    # Relative difference avoids presenting the blur band as a calibrated distance.
    difference = np.abs(depth-target)/max(target, .1)
    amount = np.clip((difference-.08)/.6, 0, 1)
    amount = np.where(np.isfinite(amount), amount, 1)
    amount = cv2.GaussianBlur(amount.astype(np.float32), (0, 0), 1.5)
    result = frame.astype(np.float32)
    levels = (0., .25, .5, .75, 1.)
    blurred = [frame] + [cv2.GaussianBlur(frame, (0, 0), strength*x) for x in levels[1:]]
    for i in range(4):
        blend = np.clip((amount-levels[i])/.25, 0, 1)[..., None]
        section = (amount >= levels[i]) & (amount <= levels[i+1])
        mix = blurred[i]*(1-blend)+blurred[i+1]*blend
        result[section] = mix[section]
    return np.clip(result, 0, 255).astype(np.uint8), amount, target


def render_cuboid(frame, depth, camera, anchor=(.72, .87), dimensions=(.8, .7, .55)):
    """Rasterize a virtual volume using perspective-correct depth and real-scene occlusion."""
    h, w = depth.shape
    u, v = int(anchor[0]*(w-1)), int(anchor[1]*(h-1))
    z = float(depth[v, u])
    if not np.isfinite(z) or z <= .1:
        raise ValueError('Ancrage sans profondeur utilisable')
    position = np.array([(u-camera['cx'])*z/camera['fx'], (v-camera['cy'])*z/camera['fy'], z])
    width, height, length = dimensions
    vertices = np.array([[x, y, zz] for zz in (0, length) for y in (0, -height)
                         for x in (-width/2, width/2)]) + position
    if (vertices[:, 2] <= .1).any():
        raise ValueError('Volume trop proche de la camera')
    uv = np.column_stack((camera['fx']*vertices[:, 0]/vertices[:, 2]+camera['cx'],
                          camera['fy']*vertices[:, 1]/vertices[:, 2]+camera['cy']))
    buffer = np.full((h, w), np.inf, np.float32)
    colors = np.zeros_like(frame)
    faces = [((0, 1, 3, 2), (190, 145, 30)), ((4, 6, 7, 5), (160, 120, 20)),
             ((0, 2, 6, 4), (220, 185, 70)), ((1, 5, 7, 3), (200, 155, 45)),
             ((2, 3, 7, 6), (235, 210, 120))]
    for face, color in faces:
        for ids in ((face[0], face[1], face[2]), (face[0], face[2], face[3])):
            p = uv[list(ids)]
            lo = np.maximum(np.floor(p.min(axis=0)).astype(int), 0)
            hi = np.minimum(np.ceil(p.max(axis=0)).astype(int), [w-1, h-1])
            if (hi < lo).any():
                continue
            yy, xx = np.mgrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
            a, b, c = p
            den = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den) < 1e-7:
                continue
            wa = ((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
            wb = ((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
            wc = 1-wa-wb
            inverse = wa/vertices[ids[0], 2]+wb/vertices[ids[1], 2]+wc/vertices[ids[2], 2]
            inside = (wa >= 0) & (wb >= 0) & (wc >= 0) & (inverse > 0)
            zz = np.divide(1., inverse, out=np.full_like(inverse, np.inf), where=inverse > 0)
            target = buffer[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
            keep = inside & (zz < target)
            target[keep] = zz[keep]
            colors[lo[1]:hi[1]+1, lo[0]:hi[0]+1][keep] = color
    virtual = np.isfinite(buffer)
    valid_real = np.isfinite(depth) & (depth > .1)
    visible = virtual & valid_real & (buffer <= depth+.03)
    result = frame.copy()
    result[visible] = (.85*colors[visible]+.15*frame[visible]).astype(np.uint8)
    return result, visible, {'anchor_normalized': list(anchor), 'dimensions_assumed_m': list(dimensions),
        'virtual_pixels': int(virtual.sum()), 'visible_pixels': int(visible.sum()),
        'occluded_or_unknown_pixels': int((virtual & ~visible).sum()),
        'anchor_depth_estimated_m': z}


class TemporalReview:
    """Debounce an alert, but never carry a reassuring state across unknown frames."""
    def __init__(self, required=3):
        self.required = required
        self.streak = 0

    def update(self, status):
        self.streak = self.streak+1 if status == 'ALERTE_SIMULEE' else 0
        if status == 'ABSTENTION':
            return 'ABSTENTION'
        if status == 'ALERTE_SIMULEE' and self.streak < self.required:
            return 'ALERTE_A_CONFIRMER'
        return status
