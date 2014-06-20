#!/usr/bin/python
import argparse, gcmodel, importlib, string

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("model", type=str,
      help="the full import path of the model to run the trace on." +
      " example: simple_malloc.SimpleMalloc")
  parser.add_argument("filename", metavar="trace.json", type=str,
      help="filename for filtered trace json. required")
  args = parser.parse_args()

  try:
    splits = args.model.split(".")
    module, name = splits[0], string.join(splits[1:], ".")
    module = importlib.import_module(module)
    args.model = getattr(module, name)
  except ImportError as e:
    parser.error("could not import module: " + str(e))
  except AttributeError as e:
    parser.error("couldn't find the model: " + str(e))
  except:
    parser.error("the model path is not valid")

  return args

if __name__ == "__main__":
  args = parse_args()
  runner = gcmodel.TraceRunner(args.filename)
  runner.register(args.model)
  results = runner.run_all()
  print results
