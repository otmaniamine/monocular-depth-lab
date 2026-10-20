import unittest
import json
import tempfile
from pathlib import Path

import cv2
import numpy as np

from application.geometry import (TemporalReview, analyse_obstacles, depth_focus,
                                  floor_plane, render_cuboid)
from pointcloud import camera_intrinsics
from application.build_examples import copy_example


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.camera = camera_intrinsics((200, 160), (200, 160), fx=180, fy=180, cx=99.5, cy=25)
        y, _ = np.indices((160, 200))
        self.depth = np.divide(1.2*180, y-25, out=np.full((160, 200), 18.), where=y>25).astype(np.float32)
        self.profile = dict(roi=(.1, .45, .9, .98), seed=(.25, .75, .75, .97),
            tolerance=.03, min_height=.15, max_height=2., max_depth=19.,
            watch_distance=6., alert_distance=3., action='Pause simulee')

    def test_floor_is_not_an_obstacle_but_raised_patch_is(self):
        plane = floor_plane(self.depth, self.camera, self.profile['seed'], .03)
        self.assertIsNotNone(plane)
        np.testing.assert_allclose(plane['normal'], [0, -1, 0], atol=1e-5)
        self.assertAlmostEqual(plane['offset'], 1.2, places=4)
        report, mask = analyse_obstacles(self.depth, self.camera, self.profile)
        self.assertEqual(report['status'], 'A_CONFIRMER')
        self.assertEqual(mask.sum(), 0)
        raised = self.depth.copy()
        raised[80:110, 80:120] = 2.
        report, mask = analyse_obstacles(raised, self.camera, self.profile)
        self.assertEqual(report['status'], 'ALERTE_SIMULEE')
        self.assertGreater(mask[85:105, 85:115].sum(), 500)
        self.assertEqual(mask[125:, :].sum(), 0)

    def test_wall_and_missing_depth_require_abstention(self):
        self.assertIsNone(floor_plane(np.full_like(self.depth, 4), self.camera))
        for depth, camera_ok in ((np.full_like(self.depth, np.nan), True),
                                 (np.full_like(self.depth, 4), True), (self.depth, False)):
            report, mask = analyse_obstacles(depth, self.camera, self.profile, camera_ok)
            self.assertEqual(report['status'], 'ABSTENTION')
            self.assertEqual(mask.sum(), 0)

    def test_temporal_alert_cannot_survive_unknown_frame(self):
        temporal = TemporalReview(3)
        self.assertEqual(temporal.update('ALERTE_SIMULEE'), 'ALERTE_A_CONFIRMER')
        temporal.update('ALERTE_SIMULEE')
        self.assertEqual(temporal.update('ALERTE_SIMULEE'), 'ALERTE_SIMULEE')
        self.assertEqual(temporal.update('ABSTENTION'), 'ABSTENTION')
        self.assertEqual(temporal.update('ALERTE_SIMULEE'), 'ALERTE_A_CONFIRMER')

    def test_focus_keeps_selected_depth_and_blurs_other_depth(self):
        y, x = np.indices((120, 160))
        checker = (((x//2+y//2) % 2)*255).astype(np.uint8)
        image = np.repeat(checker[..., None], 3, axis=2)
        depth = np.full((120, 160), 2., np.float32)
        depth[:, 80:] = 6.
        result, _, target = depth_focus(image, depth, (.25, .5))
        self.assertEqual(target, 2.)
        np.testing.assert_equal(result[:, :50], image[:, :50])
        self.assertLess(result[20:100, 110:150].std(), image[20:100, 110:150].std()/5)

    def test_real_foreground_occludes_virtual_volume(self):
        frame = np.zeros((160, 200, 3), np.uint8)
        camera = camera_intrinsics((200, 160), (200, 160), fx=160, fy=160)
        depth = np.full((160, 200), 10., np.float32)
        _, visible, details = render_cuboid(frame, depth, camera, (.5, .8), (4, 4, 3))
        self.assertGreater(details['visible_pixels'], 100)
        foreground = depth.copy()
        foreground[:, :95] = 3.
        image, partly_visible, _ = render_cuboid(frame, foreground, camera, (.5, .8), (4, 4, 3))
        self.assertLess(partly_visible.sum(), visible.sum())
        self.assertEqual(partly_visible[:, :95].sum(), 0)
        self.assertEqual(image[:, :95].sum(), 0)

    def test_gallery_rejects_private_input_and_skips_stale_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp)/'source', Path(tmp)/'target'
            source.mkdir()
            report = source/'rapport.json'
            report.write_text(json.dumps([{'source': 'entree_utilisateur'}]), encoding='utf-8')
            with self.assertRaises(ValueError):
                copy_example(source, target, 'street.jpg')
            self.assertFalse(target.exists())
            report.write_text(json.dumps([{'source': 'street.jpg'}]), encoding='utf-8')
            (source/'vue_001_comparaison.jpg').write_bytes(b'public')
            (source/'vue_002_comparaison.jpg').write_bytes(b'old private frame')
            (source/'video_annotee.mp4').write_bytes(b'old private video')
            copy_example(source, target, 'street.jpg')
            self.assertTrue((target/'vue_001_comparaison.jpg').exists())
            self.assertFalse((target/'vue_002_comparaison.jpg').exists())
            self.assertFalse((target/'video_annotee.mp4').exists())


if __name__ == '__main__':
    unittest.main()
