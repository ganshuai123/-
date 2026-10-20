"""End-to-end checks of numerical results, data handling and executable examples."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / '.agents' / 'skills' / 'geoscience-github' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from sources import source


class Workflows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='geoscience-test-')
        cls.root = Path(cls.temporary.name)
        existing = os.environ.get('GEOSCIENCE_TEST_DEMO')
        cls.demo = Path(existing).resolve() if existing else cls.root / 'demo'
        if not existing:
            result = cls.call('demo', '--out', str(cls.demo))
            if result.returncode:
                errors = {str(p.relative_to(cls.demo)): p.read_text(encoding='utf-8') for p in cls.demo.rglob('error.txt')}
                raise RuntimeError(f'Demo failed: {result.stdout}\n{result.stderr}\n{errors}')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    @staticmethod
    def call(*args):
        return subprocess.run([sys.executable, str(SCRIPTS / 'engine.py'), *args], capture_output=True, text=True, encoding='utf-8')

    def test_every_demo_has_real_nonempty_figures(self):
        for mode in ('stereonet', 'well-log', 'analyze', 'tutorial', 'petroleum', 'batch-plot'):
            with self.subTest(mode=mode):
                folder = self.demo / mode
                self.assertEqual(json.loads((folder / 'run.json').read_text(encoding='utf-8'))['status'], 'success')
                figures = list(folder.rglob('*.png'))
                self.assertTrue(figures)
                for figure in figures:
                    self.assertGreater(figure.stat().st_size, 3000)
                    self.assertTrue(figure.with_suffix('.svg').is_file())

    def test_plane_normals_known_geometries(self):
        normals = pd.read_csv(self.demo / 'stereonet' / 'unit_plane_normals.csv').to_numpy()
        np.testing.assert_allclose(np.linalg.norm(normals, axis=1), 1, atol=1e-12)
        np.testing.assert_allclose(normals[0], [0, 0, 1], atol=1e-12)
        np.testing.assert_allclose(np.abs(normals[2]), [0, 1, 0], atol=1e-12)

    def test_rhr_strike_matches_dip_direction(self):
        orientations = pd.read_csv(self.demo / 'synthetic_inputs' / 'orientations.csv')
        orientations['strike'] = (orientations.dip_direction - 90) % 360
        csv_path = self.root / 'rhr.csv'
        orientations.to_csv(csv_path, index=False)
        destination = self.root / 'rhr-result'
        self.assertEqual(self.call('stereonet', '--csv', str(csv_path), '--azimuth', 'strike', '--orientation', 'rhr-strike', '--out', str(destination)).returncode, 0)
        np.testing.assert_allclose(pd.read_csv(destination / 'unit_plane_normals.csv'), pd.read_csv(self.demo / 'stereonet' / 'unit_plane_normals.csv'), atol=1e-12)

    def test_pairwise_missing_counts(self):
        csv_path = self.root / 'missing.csv'
        pd.DataFrame({'x': [1., 2., 3.], 'y': [2., np.nan, 6.], 'z': [5., 6., np.nan]}).to_csv(csv_path, index=False)
        destination = self.root / 'missing-result'
        self.assertEqual(self.call('analyze', '--csv', str(csv_path), '--x', 'x', '--ys', 'y,z', '--out', str(destination)).returncode, 0)
        counts = pd.read_csv(destination / 'correlation_pair_counts.csv', index_col=0)
        self.assertEqual(counts.loc['x', 'y'], 2)
        self.assertEqual(counts.loc['y', 'z'], 1)
        summary = pd.read_csv(destination / 'summary.csv', index_col=0)
        self.assertEqual(summary.loc['y', 'missing'], 1)
        self.assertAlmostEqual(summary.loc['y', 'mean'], 4.)

    def test_spectral_weights_match_independent_least_squares(self):
        directory = source('petroleum') / 'Spectral Gamma-ray Logging'
        def spectra(name):
            with (directory / name).open(encoding='utf-8') as handle:
                rows = [row[0].removeprefix('SPCH 131 0 0 1234 spectre_type{5} ') for row in csv.reader(handle) if row and row[0].startswith('SPCH')]
            return np.array([[float(value) for value in row.split()] for row in rows])
        calibration = np.array([spectra(name).sum(axis=0) for name in ('k.mdb.csv', 'th.mdb.csv', 'u.mdb.csv')]).T
        sample = spectra('quest.mdb.csv').T
        expected, _, _, _ = np.linalg.lstsq(calibration, sample, rcond=None)
        actual = pd.read_csv(self.demo / 'petroleum' / 'spectral_component_weights.csv').to_numpy()
        np.testing.assert_allclose(actual, expected.T, rtol=1e-9, atol=1e-10)
        rmse = np.sqrt(np.mean((sample - calibration @ expected) ** 2, axis=0))
        np.testing.assert_allclose(pd.read_csv(self.demo / 'petroleum' / 'fit_residuals.csv').rmse_counts, rmse, rtol=1e-10)

    def test_reject_negative_log_resistivity(self):
        inputs = self.demo / 'synthetic_inputs'
        data = pd.read_csv(inputs / 'well.csv')
        data.loc[0, 'res'] = -1
        csv_path = self.root / 'invalid-well.csv'
        data.to_csv(csv_path, index=False)
        destination = self.root / 'invalid-well-result'
        result = self.call('well-log', '--csv', str(csv_path), '--well', 'SYNTHETIC-DEMO', '--units-json', str(inputs / 'units.json'), '--out', str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list(destination.glob('*.png')))
        self.assertIn('positive', json.loads((destination / 'run.json').read_text(encoding='utf-8'))['error'])

    def test_protect_existing_outputs(self):
        destination = self.root / 'existing-result'
        destination.mkdir()
        sentinel = destination / 'keep.txt'
        sentinel.write_text('retain this result', encoding='utf-8')
        result = self.call('tutorial', '--out', str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(encoding='utf-8'), 'retain this result')
        self.assertEqual(len(list(destination.iterdir())), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
