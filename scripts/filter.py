#!/usr/bin/python
"""
This script filters allocations and deallocations from an input merged mtrace
json data, that is, mtrace.json run through combine_alloc_free.py. In
particular, it keeps only label type entries and keeps/outputs only the
following keys from the entry:
  1) timestamp
  2) type: 1 for allocation, 0 for free, -1 for invalid free
  3) bytes: number of bytes being allocated or freed
  4) name: the name of the object being allocced or freed
  5) addr: the address returned by allocator that allocated this object

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
import sys, json, os, argparse
import itertools

# global constants
BAD_FREE_TYPE = -1
FREE_TYPE = 0
ALLOC_TYPE = 1

def printerr(*args):
  print(*args, file=sys.stderr)

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
  size, name, addr = label['bytes'], label['label'], label['host_addr']
  base = {"name": name, "bytes": size, "addr": addr}
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
    filtered = base.copy()
    filtered['name'] = "inv"
    filtered['type'] = BAD_FREE_TYPE
    filtered['timestamp'] = label['timestamp_free']
    yield filtered
    return

  # Must be a rouge alloc
  yield extract_alloc(base, label)
  return

def main(data, discard_invalid):
  labels = itertools.ifilter(lambda entry: entry["type"] == "label", data)
  filtered = [x for l in labels for x in filter_label(l)]

  if discard_invalid: # discard invalid entries if requested
    filtered = itertools.ifilter(lambda l: l["type"] != BAD_FREE_TYPE, filtered)

  sorted_filtered = sorted(filtered, key = lambda l: float(l['timestamp']))
  print(json.dumps(sorted_filtered))

if __name__ == "__main__":
  def boolean(string):
    """ Converts a user's input boolean to a bool if it can."""
    lowercase = string.lower()
    if lowercase == "true": return True
    elif lowercase == "false": return False
    raise argparse.ArgumentTypeError("flag must be 'true' or 'false'")

  parser = argparse.ArgumentParser()
  parser.add_argument("discard_invalid", type=boolean, default=False, nargs="?",
      help="whether or not to discard rogue/extra frees. (false)")
  parser.add_argument("filename", nargs="?", metavar="merged.json",
      type=argparse.FileType('r'), default=sys.stdin,
      help="filename for merged json. leave empty to use standard input")

  args = parser.parse_args()
  data = json.load(args.filename)
  sys.exit(main(data, args.discard_invalid))
