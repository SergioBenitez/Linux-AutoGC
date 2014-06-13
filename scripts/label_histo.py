#!/usr/bin/python

from __future__ import print_function

# Force matplotlib to not use any Xwindows backend.
import matplotlib
matplotlib.use('Agg')

import sys, json, os
import itertools
import numpy
import matplotlib.pyplot as plt

"""
The goal of this script is to take merged mtrace label entries with
timestamp_alloc and timestamp_free properties, calculate the lifetime of an
allocation (free - alloc), group the lifetimes by label name, and generate a
histrogram with a CDF overlayed on top for each of the label named.
"""

def printerr(*args):
  print(*args, file=sys.stderr)

# Returns a dict where the key is a label name and the value is an array of
# lifetime values. There is one entry for each object type.
def group_lifetimes_by_label(data):
  output = {}
  for item in data:
    # skip extra allocs/frees
    if 'extra' in item: continue

    label = item['label']
    if label not in output:
      output[label] = []
    output[label].append(get_lifetime(item))
  return output

def get_lifetime(label):
  return (label['timestamp_free'] - label['timestamp_alloc']) * 10**3

def IQR(values):
  return numpy.percentile(values, 75) - numpy.percentile(values, 25)

def freedman_diaconis_rule(values):
  return 2 * IQR(values) * (len(values)**(-1/3))

# Removes extreme outliers to get reasonable graphs
def remove_outliers(groups):
  def get_values_for_key(k):
    p = .95 # bottom percentile to keep
    sorted_values = numpy.sort(numpy.array(groups[k]))
    count = len(sorted_values)
    top_index = count if count < int(1 / (1 - p)) else count * p
    return sorted_values[:top_index]
  return get_values_for_key

# mv = mapped_values
# Removes all entries in mv with <= num elements in its value
def filter_low(mv, num):
  for key in mv:
    count = len(mv[key])
    if count <= num: printerr("Filtering out", key, "(" + str(count) + ")")
  return {key: mv[key] for key in mv if len(mv[key]) > num}

def generate_boxplot(mapped_values, filename):
  print("Generating boxplot")

  # Creating the figure object, setting titles and labels
  fig, ax1 = plt.subplots(figsize=(10,5))
  fig.canvas.set_window_title('Linux Object Lifetimes')
  ax1.set_title('Comparison of Object Lifetimes in the Linux Kernel')
  ax1.set_xlabel('Object Label')
  ax1.set_ylabel('Lifetime (milliseconds)')

  # Set the positions for the respective boundaries (bottom, left = 0, 0)
  plt.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.325)
  ax1.minorticks_on()

  # Add a horizontal grid to the plot, but make it very light in color
  ax1.yaxis.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.9)
  ax1.yaxis.grid(True, linestyle='--', which='minor', color='lightgrey', alpha=0.7)

  # Seperating keys and values
  all_values, labels = [], []
  for key in mapped_values:
    all_values.append(mapped_values[key])
    labels.append(key)

  # Setting the names for the ticks on the x-axis
  xtickNames = plt.setp(ax1, xticklabels=labels)
  plt.setp(xtickNames, rotation=90, fontsize=8)

  # Creating boxplot, setting figure colors, saving to file
  bp = plt.boxplot(all_values)
  plt.setp(bp['boxes'], color='black')
  plt.setp(bp['whiskers'], color='black')
  plt.setp(bp['fliers'], color='red', marker='+')
  plt.setp(bp['medians'], color='blue')
  plt.savefig(filename)

def generate_histogram(name, values, filename):
  print("Working on", name)

  # Calculating number of bins using Freedman-Diaconis Rule
  bin_width = freedman_diaconis_rule(values)
  amax, amin = numpy.amax(values), numpy.amin(values)
  num_bins = ((amax - amin) / float(bin_width)) / 3
  num_bins = max(min(num_bins, 120), 1)

  fig, ax1 = plt.subplots()
  ax1.set_title("Lifetime Distribution for " + name + " Objects")
  ax1.set_xlabel('Lifetime (milliseconds)')
  ax1.set_ylabel('Number of Objects')

  ax1.minorticks_on()
  ax1.xaxis.grid(True, linestyle='-', which='both', color='lightgrey', alpha=0.8)
  ax1.yaxis.grid(True, linestyle='--', which='major', color='lightgrey', alpha=0.55)

  # The histogram
  counts, bin_edges, patches = plt.hist(values, num_bins, color="white")

  # Setting up a second y-axis for the CDF
  ax2 = ax1.twinx()
  ax2.set_ylabel("CDF", rotation=-90)
  ax2.yaxis.grid(True, linestyle='--', which='major', color='b', alpha=0.35)

  # Generating a CDF to plot on top of histogram
  cdf = numpy.cumsum(counts)
  max_count, count_sum = max(counts), sum(counts)
  cdf_points = map(lambda c: float(c) / sum(counts), cdf)
  ax2.plot(bin_edges, [0] + cdf_points)

  plt.savefig(filename)

def main(data):
  groups = group_lifetimes_by_label(data)
  mapped_values = {key: remove_outliers(groups)(key) for key in groups}
  mapped_values = filter_low(mapped_values, 15) # removes objs with <= 15 vals

  # A boxplot comparing all lifetimes
  generate_boxplot(mapped_values, "boxplot.pdf")

  # A histogram for each object type
  for key in mapped_values:
    generate_histogram(key, mapped_values[key], key + "_histo.pdf")

  # print(json.dumps(groups))

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
