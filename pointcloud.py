"""Camera geometry and portable point-cloud exports (no inference dependencies)."""

import base64
import json
from pathlib import Path

import cv2
import numpy as np


def camera_intrinsics(original_size, output_size, fov=60.0, fx=None, fy=None, cx=None, cy=None):
    """Intrinsics refer to the original image; resize follows pixel-center alignment."""
    width, height = original_size
    out_width, out_height = output_size
    if min(width, height, out_width, out_height) <= 0 or not 5 < fov < 175:
        raise ValueError("Invalid image dimensions or horizontal field of view")
    if (fx is None) != (fy is None):
        raise ValueError("Supply both fx and fy")
    estimated = fx is None
    if estimated:
        fx = fy = width / (2 * np.tan(np.deg2rad(fov) / 2))
    principal_point_assumed = cx is None or cy is None
    cx = (width - 1) / 2 if cx is None else cx
    cy = (height - 1) / 2 if cy is None else cy
    if not np.isfinite([fx, fy, cx, cy]).all() or min(fx, fy) <= 0:
        raise ValueError("Intrinsics must be finite and focal lengths positive")
    sx, sy = out_width / width, out_height / height
    return {"fx": float(fx * sx), "fy": float(fy * sy),
            "cx": float((cx + 0.5) * sx - 0.5), "cy": float((cy + 0.5) * sy - 0.5),
            "estimated": estimated, "principal_point_assumed": principal_point_assumed,
            "assumed_horizontal_fov_degrees": fov if estimated else None}


def unproject(depth, bgr, camera, stride=3, near=0.1, far=80.0, edge_threshold=0.1):
    if depth.ndim != 2 or bgr.shape != (*depth.shape, 3):
        raise ValueError("Depth and color must have identical dimensions")
    if stride < 1 or near < 0 or far <= near or edge_threshold < 0:
        raise ValueError("Invalid sampling or filtering settings")
    valid = np.isfinite(depth) & (depth > near) & (depth < far)
    if edge_threshold:
        safe = np.where(valid, depth, 0).astype(np.float32)
        high = cv2.dilate(safe, np.ones((3, 3), np.uint8))
        low = cv2.erode(safe, np.ones((3, 3), np.uint8))
        valid &= (high - low) <= edge_threshold * np.maximum(safe, 1e-6)
    rows, cols = np.mgrid[0:depth.shape[0]:stride, 0:depth.shape[1]:stride]
    keep = valid[rows, cols]
    rows, cols = rows[keep], cols[keep]
    z = depth[rows, cols]
    xyz = np.column_stack(((cols - camera["cx"]) * z / camera["fx"],
                           (rows - camera["cy"]) * z / camera["fy"], z)).astype(np.float32)
    rgb = bgr[rows, cols, ::-1].copy()
    return xyz, rgb, np.column_stack((cols, rows)), valid


def pack_vertices(xyz, rgb):
    if not len(xyz) or xyz.shape != rgb.shape or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("Point cloud must contain finite XYZ and matching RGB")
    vertices = np.empty(len(xyz), dtype=[("xyz", "<f4", (3,)), ("rgb", "u1", (3,))])
    vertices["xyz"], vertices["rgb"] = xyz, rgb
    return vertices.tobytes()


def write_ply(path, xyz, rgb):
    header = ("ply\nformat binary_little_endian 1.0\ncomment camera axes: x right, y down, z forward\n"
              f"element vertex {len(xyz)}\nproperty float x\nproperty float y\nproperty float z\n"
              "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
    Path(path).write_bytes(header.encode("ascii") + pack_vertices(xyz, rgb))


def viewer_fragment(xyz, rgb, metadata, max_points=30000):
    step = max(1, int(np.ceil(len(xyz) / max_points)))
    xyz, rgb = xyz[::step], rgb[::step]
    meta = {"points": len(xyz), "model": metadata["model"],
            "estimated_camera": metadata["camera"]["estimated"], "units": "metres_estimes"}
    template = (Path(__file__).parent / "viewer3d.html").read_text(encoding="utf-8")
    return template.replace("__CLOUD_METADATA__", json.dumps(meta).replace("<", "\\u003c")).replace(
        "__CLOUD_BINARY__", base64.b64encode(pack_vertices(xyz, rgb)).decode("ascii"))


def write_viewer(path, xyz, rgb, metadata):
    fragment = viewer_fragment(xyz, rgb, metadata, max_points=120000)
    wrapper = ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
               '<meta name="viewport" content="width=device-width,initial-scale=1">'
               '<title>Exploration 3D — Monocular Depth Lab</title><style>'
               ':root{color-scheme:light dark;--background:light-dark(#f4f5f7,#13171d);'
               '--foreground:light-dark(#17212d,#e3e9ef);--border:light-dark(#c2cbd3,#495562);'
               '--muted-foreground:light-dark(#495562,#bdc8d2)}'
               'body{font:16px system-ui,sans-serif;margin:24px auto;padding:0 16px;max-width:1100px;'
               'background:var(--background);color:var(--foreground)}'
               'button,input{font:inherit}button{padding:8px 14px}label{display:flex;gap:8px;align-items:center}'
               '</style></head><body><h1>Exploration du nuage de points</h1>'
               '<p>Glissez pour tourner, utilisez la molette pour zoomer. Une seule vue de la scène est reconstruite.</p>')
    Path(path).write_text(wrapper + fragment + '</body></html>', encoding="utf-8")


def write_preview(path, xyz, rgb, yaw_degrees=25):
    """A z-buffered oblique view of the actual vertices, no invented geometry."""
    yaw = np.deg2rad(yaw_degrees)
    center = np.median(xyz, axis=0)
    rotation = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
    q = (xyz - center) @ rotation.T
    distance = max(float(np.max(np.linalg.norm(q, axis=1))) * 1.15, 1)
    z = q[:, 2] + distance
    focal = 850.0
    x = np.rint(q[:, 0] / z * focal + 600).astype(int)
    y = np.rint(q[:, 1] / z * focal + 400).astype(int)
    valid = (z > 0) & (x >= 0) & (x < 1200) & (y >= 0) & (y < 800)
    ids = np.flatnonzero(valid)
    # Far-to-near drawing makes closer samples win on shared pixels.
    order = ids[np.argsort(z[ids])[::-1]]
    output = np.full((800, 1200, 3), (27, 23, 19), dtype=np.uint8)
    for i in order:
        cv2.circle(output, (x[i], y[i]), 1, tuple(int(v) for v in rgb[i, ::-1]), -1)
    if not cv2.imwrite(str(path), output):
        raise OSError("Cannot write point-cloud preview")
