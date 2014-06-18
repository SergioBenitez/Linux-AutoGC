"""
This is the library support for running memory traces generated from mtrace
data passed through merge.py and filter.py:

  cat mtrace.out | m2json | ./merge.py 2> /dev/null | ./filter.py > trace.json

The chain above does the following:
  1) Converts the binary mtrace.out to JSON.
  2) Maps allocations to frees, identifies rogue allocs/frees.
  3) Discards unnecesary fields and categorizes by allocation/free with size.

This library provides two classes: TraceRunner, GCModel. A TraceRunner instance
runs the trace through one or more GCModels.

TODO: Add debugging flag, perhaps via env variable that:
  1) Prints out each alloc/free and the time it tooks.
  2) Prints out some statistics, like avg/variance.

TODO: Have some way for models to specify allocator parameters. Goals:
  0) The idea is for the runner to be able to adjust these to maximize perf.
  1) Should be really easy.
  2) Should be simple for the runner/gcmodel to change the params.
  3) Should be Pythonic.
"""

import os, sys, argparse, json, copy_reg, types
import multiprocessing as mp

# global constants
BAD_FREE_TYPE = -1
FREE_TYPE = 0
ALLOC_TYPE = 1

class TraceRunner(object):
  def __init__(self, filename):
    self.models = []
    self.filename = filename
    self.data = None

  def load_data(self):
    if self.data: return
    self.data = json.load(open(self.filename, 'r'))

  def register(self, model):
    self.models.append(model)

  def run_one(self, model):
    # TODO: Return better results!
    # Should seperate times by item name, bytes, etc.
    self.load_data()
    model_inst = model.__new__(model)
    model_inst.__init__()
    for item in self.data:
      ts, name, size = item['timestamp'], item['name'], item['bytes']
      if item['type'] == ALLOC_TYPE:
        model_inst.alloc(ts, name, size)
      elif item['type'] == FREE_TYPE:
        model_inst.free(ts, name, size)
    return model_inst.get_time()

  def run_all(self):
    proc_count = min(len(self.models), mp.cpu_count())
    pool = mp.Pool(processes=proc_count)
    results = pool.map(self.run_one, self.models)
    return results

class GCModel(object):
  def __init__(self):
    self.time = 0

  def add_time(self, time):
    self.time += time

  def get_time(self):
    return self.time

"""
This code below allows instance methods to be pickled so that we can use
the multiprocessing.Pool.map function.
"""

def _pickle_method(method):
  func_name = method.im_func.__name__
  obj = method.im_self
  cls = method.im_class
  return _unpickle_method, (func_name, obj, cls)

def _unpickle_method(func_name, obj, cls):
  for cls in cls.mro():
    try:
      func = cls.__dict__[func_name]
    except KeyError:
      pass
    else:
      break
  return func.__get__(obj, cls)

copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)
