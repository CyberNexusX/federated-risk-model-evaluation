import unittest

import numpy as np

from evaluate import combine, describe, run, site_summary


class EvaluationTests(unittest.TestCase):
    def test_pooled_parity_with_unequal_site_sizes(self):
        labels = np.array([1, 0, 0, 1, 1])
        scores = np.array([0.1, 0.2, 0.3, 0.5, 1.0])
        left = site_summary(labels[:1], scores[:1])
        right = site_summary(labels[1:], scores[1:])
        aggregate = describe(combine([left, right]))
        direct = describe(site_summary(labels, scores))
        for field in ("observed_rate", "mean_score", "calibration_gap", "brier"):
            self.assertAlmostEqual(aggregate[field], direct[field])
        self.assertAlmostEqual(aggregate["brier"], np.square(scores - labels).mean())
        self.assertEqual(aggregate["bins"], direct["bins"])
        self.assertEqual(aggregate["bins"][-1]["n"], 2)

    def test_invalid_scores_fail_before_binning(self):
        for scores in ([float("nan")], [1.01], [-0.01]):
            with self.assertRaises(ValueError):
                site_summary([1], scores)

    def test_network_accounting(self):
        report = run(42)
        sites = report["sites"]
        self.assertEqual(report["network"]["n"], sum(site["n"] for site in sites.values()))
        self.assertEqual(report["network"]["events"], sum(site["events"] for site in sites.values()))
        self.assertLess(sites["coastal"]["calibration_gap"], report["network"]["calibration_gap"])


if __name__ == "__main__":
    unittest.main()
