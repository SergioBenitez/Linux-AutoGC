#!/usr/bin/python
from enum import Enum
import os, sys, argparse, gcmodel, math

"""
Need the enum34 library: sudo pip install enum34
"""

class Consts(Enum):
  page_size = 4096
  page_fetch_time = 10
  alloc_time = 1
  chunk_sizes = [ 8, 16, 32, 48, 64, 96, 128, 256, 512, 1024, 2048, 4096]
  init_counts = [32, 32, 24, 16, 16, 16,   8,   8,   8,    4,    2,    1]

class SimpleMalloc(gcmodel.GCModel):
  """
  A simple malloc implementation.

  The allocator fetches memory in page-size chunks from the OS. It fulfills user
  allocation requests using memory from these pages broken into chunks.

  On allocation, the allocator checks to see if a previously allocated and now
  freed chunk of memory at least as large as the size the user requested is
  available. If there is, that chunk is returned. If there is not, the allocator
  creates a new chunk from the available memory, if any. If there is no free
  memory, the allocator requests pages from the OS.

  On free, the allocator simply adds the chunk to its list of free chunks. Every
  time 4 * page_size bytes are freed (ie, frees - allocs >= 4 * page_size), the
  allocator scans the list of chunks and returns contiguous pages to the OS.
  """
  def __init__(self):
    super(SimpleMalloc, self).__init__()
    self.memory_left = 0
    self.free_chunks = []
    self.init_chunks(Consts.chunk_sizes.value, Consts.init_counts.value)

  def init_chunks(self, sizes, counts):
    """
    Initializes the chunks for the allocator. `sizes` is an array of initial
    chunk sizes and `counts` is the number of each size to preallocate.
    """
    # TODO: Add time to do this operation.
    bytes_needed = 0
    for size, num in zip(sizes, counts):
      self.free_chunks += [size] * num
      bytes_needed += size * num
    self.fetch_pages(bytes_needed)
    self.memory_left -= bytes_needed

  def fetch_pages(self, num_bytes):
    """ Fetches enough pages to have at least `num_bytes` of free memory. """
    num = math.ceil(float(num_bytes) / Consts.page_size.value)
    self.memory_left += num * Consts.page_size.value
    self.add_time(num * Consts.page_fetch_time.value)

  def get_chunk(self, size):
    # TODO: implement this!
    return None

  def alloc(self, ts, name, size):
    # attempt to get a free chunk
    if self.get_chunk(size) != None:
      return

    # no free chunk of good size.
    # make sure we have enough memory to allocate a new chunk
    if self.memory_left < size:
      self.fetch_pages(size)

    # allocate a new chunk from the available memory
    # note, the code below doesn't do this.
    # TODO: do the above
    self.memory_left -= size
    self.add_time(Consts.alloc_time.value)

  def free(self, ts, name, size):
    # TODO: implement this correctly
    self.memory_left += size
    self.add_time(Consts.alloc_time.value)
