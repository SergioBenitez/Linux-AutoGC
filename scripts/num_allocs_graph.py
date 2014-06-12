#!/usr/bin/python
"""
This script generates a graph for each label type where the x-axis is time and
the y-axis is the number of allocations at the point in time.
"""

from __future__ import print_function
# Force matplotlib to not use any Xwindows backend.
import matplotlib
matplotlib.use('Agg')

import sys, json, os
import itertools
import numpy
import matplotlib.pyplot as plt

def printerr(*args):
  print(*args, file=sys.stderr)

if __name__ == "__main__":
  def die(message):
    printerr("Error:", message)
    printerr("usage:", sys.argv[0], "input-file")
    printerr("example:", sys.argv[0], "merged.json")
    exit(1)

  if len(sys.argv) != 2:
    die("Incorrect number of arguments.")

  try:
    filename = sys.argv[1]
    data = json.load(open(filename, "r"))
  except:
    die("Invalid file path or JSON.")

  sys.exit(main(data))
