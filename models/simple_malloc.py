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

def round_up_pow2(v):
  v -= 1
  v |= v >> 1
  v |= v >> 2
  v |= v >> 4
  v |= v >> 8
  v |= v >> 16
  v += 1
  return v

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
    self.freed = 0 # (freed - allocated memory, for releasing pages)

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
    return num

  def get_chunk(self, size):
    """ Finds the smallest valid free chunk that is <= 2 * size """
    # Assume a more optimized implementation where we do a binary search on
    # buckets where the index corresponds to the power of 2 and the value at
    # that index is the number of those chunks left.
    self.add_time(math.log(len(Consts.chunk_sizes.value), 2))

    # find the smallest valid chunk
    chunk_found = None
    for chunk in self.free_chunks:
      if chunk_found == None or size <= chunk <= chunk_found:
        chunk_found = chunk

    # if we found one, check if it's too large. should get a smaller one if so
    if chunk_found == None or chunk_found > 2 * size:
      return None

    return chunk_found

  def allocate_chunk(self, size):
    chunk_size = round_up_pow2(size)
    if self.memory_left < chunk_size:
      self.fetch_pages(chunk_size)

    self.free_chunks.append(chunk_size)
    self.memory_left -= chunk_size;
    return chunk_size

  def free_memory(self):
    return self.memory_left + sum(self.free_chunks)

  def reclaim_space(self):
    return
    # """ Reclaims any contiguous pages such that at least the initial amount
    # of preallocated memory remains free for the allocator to use."""
    # # TODO: Make this possible. Will need to keep track of which pages an
    # # allocation is coming from. Is there a simpler way?
    # # Idea: have a dict from pg_num to bytes used. When bytes used becomes zero,
    # # you know the page is free.

    # # Calculating how much memory was initially preallocated
    # # Really, ceil(init_memory / page_size) was the preallocated memory...
    # init_chunks = zip(Consts.chunk_sizes.value, Consts.init_counts.value)
    # init_memory = sum([size * num for (size, num) in init_chunks])

    # # Let's keep at least a page more than the initial memory
    # while self.free_memory() >= init_memory + Consts.page_size.value:
    #   return

    # for chunk in self.free_chunks:
    #   return #???

    # pass

  def alloc(self, size):
    # get_chunk and allocate_chunk do real work, this just removes from the
    # free list, which is a pretty inexpensive operation
    self.add_time(Consts.alloc_time.value)

    # attempt to get a free chunk
    chunk = self.get_chunk(size)
    if chunk == None: # no free chunk, allocate a new one
      chunk = self.allocate_chunk(size)

    self.free_chunks.remove(chunk)
    self.freed -= chunk
    return chunk

  def free(self, chunk):
    # reclaim_space does the real work, this just adds to the free list, which
    # is a pretty inexpensive operation
    self.add_time(Consts.alloc_time.value)

    # Return to the free list
    self.free_chunks.append(chunk)

    # Reclaim space if necessary
    self.freed += chunk
    if self.freed >= 4 * Consts.page_size.value:
      self.reclaim_space()
