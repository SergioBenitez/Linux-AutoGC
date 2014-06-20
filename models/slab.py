from enum import Enum
import math, gcmodel

class Consts(Enum):
  page_size = 4096
  page_fetch_time = 10

class SlabAllocator(object):
  # TODO: Have/test different kinds of growing strategies.
  def __init__(self, init_capacity, obj_size):
    self.init_size = init_capacity
    self.obj_size = obj_size
    self.capacity = 0 # initializes on first alloc
    self.allocated = 0

  def grow(self):
    self.capacity += self.init_size

  def alloc(self):
    """ Returns the amount of new memory allocated for this operation. """
    need_memory = (self.capacity - self.allocated) <= 0
    if need_memory:
      self.grow()

    self.allocated += 1
    return self.obj_size * self.init_size if need_memory else 0

  def free(self):
    self.allocated -= 1

  def stats(self):
    return self.capacity, self.allocated

class SlabAllocatorFamily(gcmodel.GCModel):
  """
  An allocator that uses a slab allocator for each different type.
  """
  def __init__(self):
    super(SlabAllocatorFamily, self).__init__()
    self.allocators = {} # maps a type to its slab allocator

  def fetch_pages(self, num_bytes):
    """ Fetches enough pages to have at least `num_bytes` of free memory. """
    num = math.ceil(float(num_bytes) / Consts.page_size.value)
    self.add_time(num * Consts.page_fetch_time.value)
    return num

  def get_allocator(self, type_name, obj_size):
    init_size = 10
    key = (type_name, obj_size)
    if key not in self.allocators:
      self.allocators[key] = SlabAllocator(init_size, obj_size)
    return self.allocators[key]

  def talloc(self, name, size):
    # TODO: Have the allocator itself add time?
    allocator = self.get_allocator(name, size)
    added_memory = allocator.alloc()
    self.fetch_pages(added_memory)
    return size

  def tfree(self, name, size):
    allocator = self.get_allocator(name, size)
    return allocator.free()

  def done(self):
    total_capacity, total_mem = 0, 0
    for (name, obj_size) in self.allocators:
      allocator = self.allocators[(name, obj_size)]
      cap, alloc = allocator.stats()
      total_capacity += cap * obj_size
      total_mem += alloc * obj_size
    print "Used %.2f%% of memory." %((float(total_mem) / total_capacity) * 100)
