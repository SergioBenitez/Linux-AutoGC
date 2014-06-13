#!/usr/bin/python
"""
This script generates a graph for each object type from a filtered mtrace json
file where the x-axis is time and the y-axis is number of allocations.
"""

from __future__ import print_function

# force matplotlib to not use any xwindows backend.
import matplotlib
matplotlib.use('Agg')

import sys, json, os
import itertools
import numpy as np
import matplotlib.pyplot as plt

# global constants
BAD_FREE_TYPE = -1
FREE_TYPE = 0
ALLOC_TYPE = 1

def printerr(*args):
  print(*args, file=sys.stderr)

def get_prev_count(grouped, item):
  name = item['name']
  if name in grouped:
    y_vals = grouped[name][1]
    return 0 if len(y_vals) < 1 else y_vals[-1]
  return 0

def handle_item(grouped, item):
  # only deal with valid types
  if item['type'] < 0: return

  # create the initial values if needed
  name = item['name']
  if name not in grouped:
    grouped[name] = ([], [])

  # get the previous number of allocs, insert the new
  prev_count = get_prev_count(grouped, item)
  x_vals, y_vals = grouped[name]
  x_vals.append(item['timestamp'])
  if item['type'] == ALLOC_TYPE:
    y_vals.append(prev_count + 1)
  else:
    y_vals.append(prev_count - 1)

def generate_graph(name, (x_vals, y_vals)):
  print("Generating graph for", name)

  fig, ax1 = plt.subplots()
  ax1.set_title("'" + name + "' Allocations Over Time")
  ax1.set_xlabel('Time')
  ax1.set_ylabel('Number of Allocations')

  lines = ax1.plot(x_vals, y_vals)
  plt.setp(lines, aa=False, ls='steps', c='black')

  plt.savefig(name + "_allocs_time.pdf")

# remove entries with < num values
def filter_low(grouped, num):
  to_remove = []
  for k in grouped:
    if len(grouped[k][0]) < num:
      printerr("Skipping", k, "(" + str(len(grouped[k][0])) + ")")
      to_remove.append(k)

  for k in to_remove:
    del grouped[k]

def generate_union_graph(grouped):
  print("Generating union graph")

  fig, ax1 = plt.subplots()
  ax1.set_title("Allocations Over Time")
  ax1.set_xlabel('Time')
  ax1.set_ylabel('Number of Allocations')

  colormap = plt.cm.gist_rainbow
  color_cycle = [colormap(i) for i in np.linspace(0, 0.9, len(grouped))]
  plt.gca().set_color_cycle(color_cycle)
  ls = itertools.cycle(["--", ":", "-"])

  names = []
  for name in grouped:
    names.append(name)
    lines = ax1.plot(*grouped[name], ls=ls.next())
    # plt.setp(lines, aa=False, ls='steps', c='black')

  plt.legend(names, loc='upper left', ncol=4, prop={'size':8},
    columnspacing=1.0, labelspacing=0.0,
    handletextpad=0.0, handlelength=1.5)
  plt.savefig("all_allocs_time.pdf")


def main(data):
  # map from label name to a ([x-values], [y-values])
  # where x-values are time and y-values are number of allocs at that time
  grouped = {}
  for item in data:
    handle_item(grouped, item)

  # remove those with too few entries
  filter_low(grouped, 15)

  # plot each individually
  # for name in grouped:
  #   generate_graph(name, grouped[name])

  # plot them all together
  generate_union_graph(grouped)

if __name__ == "__main__":
  def die(*message):
    printerr("Error:", *message)
    printerr("usage:", sys.argv[0], "input-file")
    printerr("example:", sys.argv[0], "filtered.json")
    exit(1)

  if len(sys.argv) != 2:
    die("Incorrect number of arguments. Expected 2, got ", len(sys.argv))

  try:
    filename = sys.argv[1]
    data = json.load(open(filename, "r"))
  except:
    die("Invalid file path or JSON.")

  sys.exit(main(data))
