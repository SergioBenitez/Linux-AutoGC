#!/bin/sh
trace=$1

function die() {
  echo $1
  echo "Usage: $0 trace-filename"
  echo "Example: $0 trace.json"
  exit 1
}

if ! [ -e $trace ] || [ -z $trace ]; then
  die "Trace file could not be found."
  exit 1
fi

./runtrace.py simple_malloc.SimpleMalloc $trace
./runtrace.py slab.SlabAllocatorFamily $trace
