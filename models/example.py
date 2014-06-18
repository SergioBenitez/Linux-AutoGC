#!/usr/bin/python
import argparse, gcmodel
import simple_malloc as sm

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("filename", metavar="trace.json", type=str,
      help="filename for filtered trace json. required")
  return parser.parse_args()

if __name__ == "__main__":
  args = parse_args()
  runner = gcmodel.TraceRunner(args.filename)
  runner.register(sm.SimpleMalloc)

  results = runner.run_all()
  print results
