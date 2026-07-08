import unittest

from scripts.segments import split_target, UnknownSegmentError, ALL_SEGMENTS


class SplitTargetTests(unittest.TestCase):
    def test_split_target_default_sweep_sums_to_target(self):
        allocation = split_target(15)
        self.assertEqual(sum(allocation.values()), 15)
        self.assertEqual(set(allocation.keys()), set(ALL_SEGMENTS))

    def test_split_target_weights_high_segments_more_than_low(self):
        allocation = split_target(20)
        self.assertGreater(allocation["healthcare"], allocation["consultancies"])
        self.assertEqual(allocation["healthcare"], allocation["finance"])
        self.assertEqual(allocation["healthcare"], allocation["legal"])
        self.assertEqual(allocation["healthcare"], allocation["ai-native"])

    def test_split_target_with_explicit_segments_splits_evenly(self):
        allocation = split_target(10, segments=["healthcare", "legal"])
        self.assertEqual(allocation, {"healthcare": 5, "legal": 5})

    def test_split_target_unknown_segment_raises(self):
        with self.assertRaises(UnknownSegmentError):
            split_target(10, segments=["not-a-segment"])

    def test_split_target_small_target_still_sums_correctly(self):
        allocation = split_target(3)
        self.assertEqual(sum(allocation.values()), 3)


if __name__ == "__main__":
    unittest.main()
