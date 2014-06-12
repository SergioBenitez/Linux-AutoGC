#! /usr/bin/python
from __future__ import print_function
import umsgpack, os, sys, json

def printerr(*args):
  print(*args, file=sys.stderr)

# Converts a json file into a msgpack file.
if __name__ == "__main__":
  def die(message):
    printerr("Error:", message)
    printerr("usage:", sys.argv[0], "input-file")
    printerr("example:", sys.argv[0], "file.json")
    exit(1)

  if len(sys.argv) != 2:
    die("Incorrect number of arguments.")

  try:
    filename = sys.argv[1]
    data = json.load(open(filename, "r"))
  except:
    die("Invalid file path or JSON.")

  try:
    msgpack_data = umsgpack.packb(data)
    with open(os.path.splitext(filename)[0] + ".msgpack", 'w') as f:
      f.write(msgpack_data)
  except:
    die("Error writing out msgpack file.")
