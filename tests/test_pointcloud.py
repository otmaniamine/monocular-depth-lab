import tempfile
import unittest
from pathlib import Path

import numpy as np

from pointcloud import camera_intrinsics, unproject, write_ply


class GeometryTests(unittest.TestCase):
    def test_known_plane_and_reprojection(self):
        depth = np.full((3, 3), 2.0, np.float32)
        bgr = np.full((3, 3, 3), [1, 2, 3], np.uint8)
        k = camera_intrinsics((3, 3), (3, 3), fx=2, fy=2)
        xyz, rgb, uv, _ = unproject(depth, bgr, k, stride=1, edge_threshold=0)
        np.testing.assert_allclose(xyz[4], [0, 0, 2])
        np.testing.assert_allclose(xyz[0], [-1, -1, 2])
        np.testing.assert_equal(rgb[0], [3, 2, 1])
        back = np.column_stack((xyz[:, 0] * k['fx'] / xyz[:, 2] + k['cx'], xyz[:, 1] * k['fy'] / xyz[:, 2] + k['cy']))
        np.testing.assert_allclose(back, uv)

    def test_intrinsics_resize_preserves_camera_rays(self):
        a = camera_intrinsics((100, 80), (100, 80), fx=80, fy=90, cx=48, cy=38)
        b = camera_intrinsics((100, 80), (50, 40), fx=80, fy=90, cx=48, cy=38)
        u, v = 20.0, 16.0
        np.testing.assert_allclose([(u-a['cx'])/a['fx'], (v-a['cy'])/a['fy']],
                                   [(((u+.5)*.5-.5)-b['cx'])/b['fx'], (((v+.5)*.5-.5)-b['cy'])/b['fy']])
        self.assertFalse(b['estimated'])
        self.assertFalse(b['principal_point_assumed'])

    def test_invalid_and_far_depths_are_removed(self):
        depth = np.array([[np.nan, np.inf, -1, 0, .05, 2, 100]], np.float32)
        k = camera_intrinsics((7, 1), (7, 1))
        xyz, _, _, valid = unproject(depth, np.zeros((1, 7, 3), np.uint8), k, stride=1, near=.1, far=80, edge_threshold=0)
        self.assertEqual(len(xyz), 1)
        self.assertEqual(valid.sum(), 1)
        self.assertTrue(np.isfinite(xyz).all())

    def test_depth_jump_filter_and_binary_ply(self):
        depth = np.ones((5, 6), np.float32)
        depth[:, 3:] = 10
        k = camera_intrinsics((6, 5), (6, 5))
        xyz, rgb, _, mask = unproject(depth, np.zeros((5, 6, 3), np.uint8), k, stride=1, edge_threshold=.1)
        self.assertFalse(mask[:, 2:4].any())
        self.assertEqual(len(xyz), 20)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cloud.ply'
            write_ply(path, xyz, rgb)
            header, payload = path.read_bytes().split(b'end_header\n')
            self.assertIn(b'element vertex 20', header)
            self.assertEqual(len(payload), 20 * 15)
            record = np.frombuffer(payload, dtype=[('xyz', '<f4', (3,)), ('rgb', 'u1', (3,))])
            np.testing.assert_allclose(record['xyz'], xyz)
            np.testing.assert_equal(record['rgb'], rgb)

    def test_invalid_calibration_is_rejected(self):
        for kwargs in [dict(fx=0, fy=1), dict(fx=2), dict(fov=180), dict(cx=float('nan'))]:
            with self.assertRaises(ValueError):
                camera_intrinsics((100, 100), (50, 50), **kwargs)


if __name__ == '__main__':
    unittest.main()
