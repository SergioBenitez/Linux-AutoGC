#!/usr/bin/python
"""
This script filters allocations and deallocations from the input mtrace json
data. In particular, it keeps only label type entries and keeps/outputs only
the following keys from the entry:
  1) timestamp
  2) type: 1 for allocation, 0 for free, -1 for invalid free
  3) bytes: number of bytes being allocated or freed
  4) name: the name of the object being allocced or freed

The filtering discards frees of a type that have no previous allocation if the
discard free flag is true, otherwise it sets their type to -1. That is, if there
is an object of type 'thing' and it is freed without a previous allocation for
an object of type 'thing', the deallocation is filtered out of the data set. In
essence, this script provides a filtered memory trace containing only the
essential data to model garbage collectors on.

TODO: Get some kind of stack size/position data for allocators that need to
scan the stack.
"""

from __future__ import print_function
import sys, json, os
import itertools

# global constants
BAD_FREE_TYPE = -1
FREE_TYPE = 0
ALLOC_TYPE = 1

def printerr(*args):
  print(*args, file=sys.stderr)

# Tries to determine how many bytes this allocation or deallocation uses
def determine_free_bytes(label):
  # If there's a corresponding allocation by address, use that size.
  # Otherwise, use the last known size for the label name
  host_addr, name = label['host_addr'], label['label']
  if host_addr in addr_mem:
    num_bytes = addr_mem[host_addr]
    del addr_mem[host_addr]
    return num_bytes
  elif name in label_size:
    return label_size[name]

  printerr("Free passed to determine_bytes with no previous allocation.")
  sys.exit(1)

def extract_alloc(base, label):
  alloc = base.copy()
  alloc['type'] = ALLOC_TYPE
  alloc['timestamp'] = label['timestamp_alloc']
  return alloc

def extract_free_from_merged(base, label):
  free = base.copy()
  free['type'] = FREE_TYPE
  free['timestamp'] = label['timestamp_free']
  return free

def filter_label(label):
  # Figure out if we're dealing with a matched alloc/free pair
  label_bytes, label_name = label['bytes'], label['label']
  base = {"name": label_name, "bytes": label_bytes}
  if 'timestamp_free' in label and 'timestamp_alloc' in label:
    yield extract_alloc(base, label)
    yield extract_free_from_merged(base, label)
    return

  # Must be a rouge alloc/free. Make sure.
  if 'extra' not in label:
    printerr("Label wasn't merged nor declared as extra!")
    sys.exit(1)

  # Do we have a rouge free?
  if 'timestamp_free' in label:
    filtered = {}
    filtered['name'] = "inv"
    filtered['timestamp'] = label['timestamp_free']
    filtered['type'] = BAD_FREE_TYPE
    filtered['bytes'] = 0
    yield filtered
    return

  # Must be a rouge alloc
  yield extract_alloc(base, label)
  return

def main(data, discard_invalid):
  labels = itertools.ifilter(lambda entry: entry["type"] == "label", data)
  filtered = [x for l in labels for x in filter_label(l)]

  if discard_invalid == "true": # discard invalid entries if requested
    filtered = itertools.ifilter(lambda l: l["type"] != BAD_FREE_TYPE, filtered)

  sorted_filtered = sorted(filtered, key = lambda l: float(l['timestamp']))
  print(json.dumps(sorted_filtered))

if __name__ == "__main__":
  def die(message):
    printerr("Error:", message)
    printerr("usage:", sys.argv[0], "input-file discard-invalid")
    printerr("example:", sys.argv[0], "merged.json true")
    exit(1)

  def check_bool_flag(flag):
    if flag != "true" and flag != "false":
      die("Flags must be either 'true' or 'false'")

  if len(sys.argv) != 3:
    die("Incorrect number of arguments.")

  discard_invalid = sys.argv[2]
  check_bool_flag(discard_invalid)

  try:
    filename = sys.argv[1]
    data = json.load(open(filename, "r"))
  except:
    die("Invalid file path or JSON.")

  sys.exit(main(data, discard_invalid))
