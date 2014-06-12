#!/usr/bin/python

from __future__ import print_function
import sys, json, os
import itertools

# The goal of this script is to combine the allocation and free calls of an
# object (mtrace entries with type 'label') into one mtrace entry with both
# timestamps present. For example, consider the following two mtrace entries,
# one for the ellocation of the object, and the latter for the free:
#
# { 
#   "timestamp": 1401904885.633304,
#   "cpu": 0,
#   "access_count": 0,
#   "type": "label",
#   "label_type": 1,
#   "label": "kmalloc-256",
#   "pc": "0xffffffff81127d43",
#   "host_addr": "0x7fbc293c6e00",
#   "guest_addr": "0xffff880007bcce00",
#   "bytes": 256
# }
#
# {
#   "timestamp": 1401904885.891706,
#   "cpu": 0,
#   "access_count": 0,
#   "type": "label",
#   "label_type": 1,
#   "label": "",
#   "pc": "0xffffffff811279be",
#   "host_addr": "0x7fbc293c6e00",
#   "guest_addr": "0xffff880007bcce00",
#   "bytes": 0
# }
#
# These will be combined into the single entry:
# { 
#   "alloc_timestamp": 1401904885.633304,
#   "free_timestamp": 1401904885.891706,
#   "cpu": 0,
#   "access_count": 0,
#   "type": "label",
#   "label_type": 1,
#   "label": "kmalloc-256",
#   "pc": "0xffffffff81127d43",
#   "host_addr": "0x7fbc293c6e00",
#   "guest_addr": "0xffff880007bcce00",
#   "bytes": 256
# }
#
# The original allocation and free entries will not appear in the output. Only
# entries with type 'label' will be output. If an alloc does not have a
# corresponding free entry, it will be discarded if discardAllocFlag=true,
# otherwise it will be appended to the end of the trace. If a free entry does
# not have a corresponding alloc, it will be discarded if discardFreeFlag=true,
# otherwise it will be appended to the end of the stream. If either of these
# are appended to the end of the trace, they will be appended with the key
# 'extra' set to true.

def printerr(*args):
  print(*args, file=sys.stderr)

def main(data, discardAllocsFlag, discardFreesFlag):
  labels = itertools.ifilter(lambda entry: entry["type"] == "label", data)
  results = handle_labels(labels, discardAllocsFlag, discardFreesFlag)
  jsonString = json.dumps(results)
  print(jsonString)

def handle_labels(labels, discardExtraAllocs, discardExtraFrees):
  output = [] # Merged alloc/frees
  allocs = {} # Allocations keyed by host_addr
  extraFrees = [] # Frees that did not have an allocation
  for label in labels:
    if label['bytes'] > 0:
      handle_alloc(allocs, label)
    else:
      handle_free(allocs, output, label, extraFrees)

  if discardExtraAllocs == "false":
    for v in allocs.values(): v['extra'] = True
    output += allocs.values()

  if discardExtraFrees == "false":
    for v in extraFrees: v['extra'] = True
    output += extraFrees

  return output

def handle_alloc(allocs, label):
  host_addr = label['host_addr']

  # Check if allocation previously seen. If so, save it in 'others' array.
  if host_addr in allocs:
    savedLabel = allocs[host_addr]
    label['others'] = savedLabel
    if "others" in savedLabel:
      label['others'] += savedLabel['others']
      del savedLabel['others']

    # Debug output
    printerr("I've seen", host_addr, "before")
    printerr(savedLabel, "\n")

  # Replace 'timestamp' key with 'timestamp_alloc'
  label['timestamp_alloc'] = label['timestamp']
  del label['timestamp']

  # Replace previous with new one, or if first time, just save it in there.
  allocs[host_addr] = label

def handle_free(allocs, output, label, extraFrees):
  # Replace 'timestamp' key with 'timestamp_free'
  label['timestamp_free'] = label['timestamp']
  del label['timestamp']

  # If we haven't seen an allocation for this free, add it to 'extraFrees'
  host_addr = label['host_addr']
  if host_addr not in allocs:
    printerr("No Alloc for Host Address:", host_addr)
    extraFrees.append(label)
    return

  # Merging
  newLabel = allocs[host_addr]
  newLabel['timestamp_free'] = label['timestamp_free']

  del allocs[host_addr]
  output.append(newLabel)

if __name__ == "__main__":
  def die(message):
    printerr("Error:", message)
    printerr("usage:", sys.argv[0], "input-file discard-allocs discard-frees")
    printerr("example:", sys.argv[0], "mtrace.json true true")
    exit(1)

  def checkBoolFlag(flag):
    if flag != "true" and flag != "false":
      die("Flags must be either 'true' or 'false'")

  if len(sys.argv) != 4:
    die("Incorrect number of arguments.")

  discardAllocsFlag, discardFreesFlag = sys.argv[2:4]
  checkBoolFlag(discardAllocsFlag)
  checkBoolFlag(discardFreesFlag)

  try:
    filename = sys.argv[1]
    data = json.load(open(filename, "r"))
  except:
    die("Invalid file path or JSON.")

  sys.exit(main(data, discardAllocsFlag, discardFreesFlag))
