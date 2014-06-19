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

import os, sys, argparse, json, copy_reg, types, inspect
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
      item_type, addr = item['type'], item['addr']
      ts, name, size = item['timestamp'], item['name'], item['bytes']
      if item_type == ALLOC_TYPE:
        model_inst._alloc(ts, addr, name, size)
      elif item_type == FREE_TYPE:
        model_inst._free(ts, addr, name, size)
    return model_inst.get_time()

  def run_all(self):
    proc_count = min(len(self.models), mp.cpu_count())
    pool = mp.Pool(processes=proc_count)
    results = pool.map(self.run_one, self.models)
    # results = [self.run_one(model) for model in self.models]
    return results

class GCModel(object):
  def __init__(self):
    self._time = 0
    self._metadata = {} # map addresses to returned allocation metadata
    self._validate_callbacks("talloc", "alloc", 3, 2)
    self._validate_callbacks("tfree", "free", 3, 2)

  def _get_method(self, name):
    try:
      return getattr(self, name)
    except AttributeError:
      return None

  def _validate_callbacks(self, a, b, anum, bnum):
    """
    Makes sure that only one of methods a and b are defined. Makes sure that
    the method defined has the correct number of arguments (anum, bnum).
    """
    f_a, f_b = self._get_method(a), self._get_method(b)
    has_a, has_b = f_a != None, f_b != None
    if has_a and has_b:
      raise AssertionError("Cannot define both " + a + ", and " + b + ".")
    elif has_a:
      fargs, _, _, _ = inspect.getargspec(f_a)
      if len(fargs) != anum:
        raise AssertionError(a + " must take exactly " + str(anum) + " args.")
    elif has_b:
      fargs, _, _, _ = inspect.getargspec(f_b)
      if len(fargs) != bnum:
        raise AssertionError(b + " must take exactly " + str(bnum) + " args.")
    else:
      raise AssertionError("Must define one of " + a + " or " + b + ".")

  def add_time(self, time):
    self._time += time

  def get_time(self):
    return self._time

  def _alloc(self, ts, addr, name, size):
    # relies on _validate_callbacks being run before
    uses_simple = self._get_method("alloc") != None
    if uses_simple:
      metadata = self.alloc(size)
    else:
      metadata = self.talloc(name, size)
    self._metadata[addr] = metadata

  def _free(self, ts, addr, name, size):
    # relies on _validate_callbacks being run before
    uses_simple = self._get_method("free") != None
    metadata = self._metadata[addr]
    if uses_simple:
      self.free(metadata)
    else:
      self.tfree(name, metadata)
    del self._metadata[addr]

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
