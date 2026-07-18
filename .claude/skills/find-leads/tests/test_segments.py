import unittest

from scripts.segments import split_target, UnknownSegmentError, ALL_SEGMENTS

DEFAULT_WEIGHTS = {"icp1": 2, "icp2": 2, "icp3": 1}


class SplitTargetTests(unittest.TestCase):
    def test_split_target_weighted_sweep_sums_to_target(self):
        allocation = split_target(20, weights=DEFAULT_WEIGHTS)
        self.assertEqual(sum(allocation.values()), 20)
        self.assertEqual(set(allocation.keys()), set(ALL_SEGMENTS))

    def test_split_target_weights_icp1_and_icp2_equally_above_icp3(self):
        allocation = split_target(20, weights=DEFAULT_WEIGHTS)
        self.assertEqual(allocation["icp1"], allocation["icp2"])
        self.assertGreater(allocation["icp1"], allocation["icp3"])

    def test_split_target_matches_2_2_1_ratio(self):
        allocation = split_target(10, weights=DEFAULT_WEIGHTS)
        self.assertEqual(allocation, {"icp1": 4, "icp2": 4, "icp3": 2})

    def test_split_target_with_explicit_segments_splits_evenly(self):
        allocation = split_target(10, segments=["icp1", "icp2"])
        self.assertEqual(allocation, {"icp1": 5, "icp2": 5})

    def test_split_target_unknown_segment_raises(self):
        with self.assertRaises(UnknownSegmentError):
            split_target(10, segments=["not-a-segment"])

    def test_split_target_small_target_still_sums_correctly(self):
        allocation = split_target(3, weights=DEFAULT_WEIGHTS)
        self.assertEqual(sum(allocation.values()), 3)

    def test_split_target_without_weights_or_segments_raises(self):
        with self.assertRaises(ValueError):
            split_target(10)

    def test_split_target_weights_missing_a_segment_raises(self):
        with self.assertRaises(UnknownSegmentError):
            split_target(10, weights={"icp1": 2, "icp2": 2})

    def test_split_target_weights_with_non_positive_value_raises(self):
        with self.assertRaises(ValueError):
            split_target(10, weights={"icp1": 2, "icp2": 2, "icp3": 0})


if __name__ == "__main__":
    unittest.main()
