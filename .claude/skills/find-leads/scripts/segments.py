"""Segment (ICP) weighting for discover-mode target-count splitting.

Weights are NOT hardcoded here. The relative priority across ICP1/ICP2/
ICP3 is a sales-priority judgment call, not a stable ICP definition — see
docs/brand/personas.md's ICP framing for the current priority language.
SKILL.md's "ICP segments & weights" section instructs whoever runs
`discover` to read that framing and decide weights fresh each run,
passing them in via --weights. This module only owns the arithmetic:
turning a target count + weights into integer per-segment allocations.
"""

import argparse
import json

ALL_SEGMENTS = ["icp1", "icp2", "icp3"]


class UnknownSegmentError(ValueError):
    pass


def split_target(target: int, weights: dict = None, segments: list = None) -> dict:
    """Split `target` leads across segments.

    If `segments` is given, split evenly across exactly those segments
    (ignoring `weights`). Elif `weights` is given, it must have exactly
    one positive-integer entry per name in ALL_SEGMENTS; split
    proportionally to those weights. If neither is given, raise
    ValueError — callers must decide a weighting explicitly.
    Uses the largest-remainder method so allocations always sum exactly
    to `target`.
    """
    if segments is not None:
        for s in segments:
            if s not in ALL_SEGMENTS:
                raise UnknownSegmentError(f"Unknown segment {s!r}; expected one of {ALL_SEGMENTS}")
        weights_used = {s: 1 for s in segments}
    elif weights is not None:
        if set(weights) != set(ALL_SEGMENTS):
            raise UnknownSegmentError(
                f"--weights must have exactly one entry per segment {ALL_SEGMENTS}; got {sorted(weights)}"
            )
        for s, w in weights.items():
            if not isinstance(w, int) or w <= 0:
                raise ValueError(f"weight for {s!r} must be a positive integer, got {w!r}")
        weights_used = weights
    else:
        raise ValueError("split_target requires either `weights` or `segments` — no default weighting exists")

    total_weight = sum(weights_used.values())
    raw = {s: target * w / total_weight for s, w in weights_used.items()}
    floors = {s: int(v) for s, v in raw.items()}
    remainder = target - sum(floors.values())

    remainders_sorted = sorted(weights_used, key=lambda s: raw[s] - floors[s], reverse=True)
    for s in remainders_sorted[:remainder]:
        floors[s] += 1

    return floors


def _parse_weights(s):
    result = {}
    for pair in s.split(","):
        k, v = pair.split("=")
        result[k.strip()] = int(v.strip())
    return result


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Split a discover-mode target across ICP segments")
    parser.add_argument("--target", type=int, required=True)
    parser.add_argument("--weights", help="comma-separated per-segment weights, e.g. icp1=2,icp2=2,icp3=1")
    parser.add_argument("--segments", help="comma-separated segment override (splits evenly, ignores --weights)")
    args = parser.parse_args(argv)

    if args.segments and args.weights:
        parser.error("pass exactly one of --weights or --segments, not both")
    if not args.segments and not args.weights:
        parser.error("pass exactly one of --weights or --segments")

    segments = args.segments.split(",") if args.segments else None
    weights = _parse_weights(args.weights) if args.weights else None
    print(json.dumps(split_target(args.target, weights=weights, segments=segments)))


if __name__ == "__main__":
    _cli()
