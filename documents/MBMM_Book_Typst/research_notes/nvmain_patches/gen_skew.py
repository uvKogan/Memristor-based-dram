#!/usr/bin/env python3
"""Regenerate the skewed wear-map trace: 20,000 writes, 80% to one hot
address. Source of truth for skew.nvt (see README.md)."""
import argparse, os, random

NUM_REQUESTS, HOT_ADDR, SPACE, HOT_PROB = 20000, 0x40, 0x100000, 0.8
DATA = "0" * 128

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default=os.path.join(here, "skew.nvt"))
    p.add_argument("--seed", type=int, default=1234)
    args = p.parse_args()

    rng = random.Random(args.seed)
    with open(args.out, "w") as f:
        for i in range(NUM_REQUESTS):
            addr = HOT_ADDR if rng.random() < HOT_PROB else rng.randrange(0, SPACE, 64)
            f.write(f"{i * 4} W {hex(addr)} {DATA} 0\n")
