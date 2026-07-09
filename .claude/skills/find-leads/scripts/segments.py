"""Segment (ICP) weighting for discover-mode target-count splitting.

Weights reflect priority sequencing from the ICP base: ICP1 and ICP2 are
where the team spends now (equal weight), ICP3 is seeded at a lighter
weight since it's pipeline-building for the Authorization Broker, not
actively closed yet.
"""

import argparse
import json

SEGMENT_WEIGHTS = {
    "icp1": 2,
    "icp2": 2,
    "icp3": 1,
}

ALL_SEGMENTS = list(SEGMENT_WEIGHTS)


class UnknownSegmentError(ValueError):
    pass


def split_target(target: int, segments=None) -> dict:
    """Split `target` leads across segments.

    If `segments` is given, split evenly across exactly those segments
    (ignoring weights). Otherwise, split across ALL_SEGMENTS proportional
    to SEGMENT_WEIGHTS. Uses the largest-remainder method so allocations
    always sum exactly to `target`.
    """
    if segments is not None:
        for s in segments:
            if s not in SEGMENT_WEIGHTS:
                raise UnknownSegmentError(f"Unknown segment {s!r}; expected one of {ALL_SEGMENTS}")
        weights = {s: 1 for s in segments}
    else:
        weights = SEGMENT_WEIGHTS

    total_weight = sum(weights.values())
    raw = {s: target * w / total_weight for s, w in weights.items()}
    floors = {s: int(v) for s, v in raw.items()}
    remainder = target - sum(floors.values())

    remainders_sorted = sorted(weights, key=lambda s: raw[s] - floors[s], reverse=True)
    for s in remainders_sorted[:remainder]:
        floors[s] += 1

    return floors


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Split a discover-mode target across ICP segments")
    parser.add_argument("--target", type=int, required=True)
    parser.add_argument("--segments", help="comma-separated segment override")
    args = parser.parse_args(argv)
    segments = args.segments.split(",") if args.segments else None
    print(json.dumps(split_target(args.target, segments)))


if __name__ == "__main__":
    _cli()
