"""Various utility functions."""
import math


def gps_coord_mdiff(p1: "(lat, lon)", p2: "(lat, lon)"):
    """Calculate the (rough) x,y meter difference from two GPS coordinate points (p1, to p2)."""
    return (111320. * math.cos(math.radians(p1[0])) * (p2[1] - p1[1]),  # x
            110540. * (p2[0] - p1[0]))  # y
