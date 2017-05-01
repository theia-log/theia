"""
Provides:
1. Atomic file write:
  - May squash couple of events together
  - It is asynchronous
  - Small lock window when the rename of the file is done
2. Store Reader
  - per store file

3. Store API:
  - Store event
  - Find event by ID
  - Search Events by filter
"""

from tempfile import NamedTemporaryFile
from io import BytesIO
from threading import Lock
from shutil import move
from os.path import join as join_paths

from theia.storeapi import EventStore


class SequentialEventReader:
  
  def __init__(self, stream):
    pass
  
  def events(self):
    pass
  
  def events_no_content(self):
    pass
  
  def curr_event(self):
    pass


class MemoryFile:
  
  def __init__(self, name, path):
    self.name = name
    self.path = path
    self.buffer = BytesIO()
    self.lock = Lock()
  
  def write(self, obj):
    try:
      self.lock.acquire()
      self.buffer.write(obj)
    finally:
      self.lock.release()
  
  def stream(self):
    # copy the buffer
    # return the copy
    try:
      self.lock.acquire()
      return BytesIO(self.buffer.getvalue())
    finally:
      self.lock.release()
  
  def flush(self):
    tmpf = NamedTemporaryFile(dir=self.path)
    try:
      self.lock.acquire()
      tmpf.write(self.buffer.getvalue())
      tmpf.flush()
      move(tmpf.name, join_paths(self.path, self.name))
    finally:
      self.lock.release()


class NaiveEventStore(EventStore):
  
  def __init__(self, root_dir):
    self.root_dir = root_dir


