import unittest

from scripts.segments import split_target, UnknownSegmentError, ALL_SEGMENTS


class SplitTargetTests(unittest.TestCase):
    def test_split_target_default_sweep_sums_to_target(self):
        allocation = split_target(20)
        self.assertEqual(sum(allocation.values()), 20)
        self.assertEqual(set(allocation.keys()), set(ALL_SEGMENTS))

    def test_split_target_weights_icp1_and_icp2_equally_above_icp3(self):
        allocation = split_target(20)
        self.assertEqual(allocation["icp1"], allocation["icp2"])
        self.assertGreater(allocation["icp1"], allocation["icp3"])

    def test_split_target_matches_40_40_20_ratio(self):
        allocation = split_target(10)
        self.assertEqual(allocation, {"icp1": 4, "icp2": 4, "icp3": 2})

    def test_split_target_with_explicit_segments_splits_evenly(self):
        allocation = split_target(10, segments=["icp1", "icp2"])
        self.assertEqual(allocation, {"icp1": 5, "icp2": 5})

    def test_split_target_unknown_segment_raises(self):
        with self.assertRaises(UnknownSegmentError):
            split_target(10, segments=["not-a-segment"])

    def test_split_target_small_target_still_sums_correctly(self):
        allocation = split_target(3)
        self.assertEqual(sum(allocation.values()), 3)


if __name__ == "__main__":
    unittest.main()
