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
from os import listdir
from collections import namedtuple
import re

from theia.storeapi import EventStore
from theis.model import EventSerializer


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


DataFile = namedtuple('DataFile', ['path','start','end'])

def binary_search(datafiles, ts):
  start = 0
  end = len(datafiles)-1
  if not len(datafiles):
    return None
  if datafiles[0].start > ts or datafiles[-1].end < ts:
    return None
  
  while True:
    mid = (end+start)//2
    #print(start, end, mid)
    if datafiles[mid].end >= ts:
      #print('end=mid')
      end = mid
    else:
      start = mid
      #print('start=mid')
    if end - start <= 1:
      if ts > datafiles[start].end and ts < datafiles[end].start:
        return None
      if datafiles[start].end >= ts:
        return start
      else:
        return end
  return None


class FileIndex:
  def __init__(self, root_dir):
    self.root = root_dir
    self.files = self._load_files(root_dir)
  
  def _load_files(self, root_dir):
    files = []
    
    for fn in listdir(root_dir):
      df = self._load_data_file(fn)
      if df:
        files.append(df)

    files = sorted(files, key=lambda n: n.start)
    print('Loaded %d files to index.'%len(files))
    if len(files):
      print('Spanning from %d to %d' % (files[0].start, files[-1].end))
    return files
  
  def _load_data_file(self, fname):
    if re.match('\d+-\d+', fname):
      start,_,end = fname.partition('-')
      start,end = int(start),int(end)
      return DataFile(path=join_paths(self.root, fname), start=start, end=end)
    return None

  def find(self, ts_from, ts_to):
    idx = binary_search(self.files, ts_from)
    if idx is not None:
      found = []
      while idx < len(self.files):
        df = self.files[idx]
        if df.start <= ts_from:
          found.append(df)
        if df.end > ts_to:
          break
      return found
    return None
  
  def find_event_file(self, ts_from):
    idx = binary_search(self.files, ts_from)
    if idx is not None:
      return idx[-1]
    return None
  
  def add_file(self, fname):
    df = self._load_data_file(fname)
    if df:
      self.files.append(df)
      self.files = sorted(files, key=lambda n: n.start)


class NaiveEventStore(EventStore):

  def __init__(self, root_dir):
    self.root_dir = root_dir
    self.data_file_interval = 60*1000 # 60 seconds 
    self.serializer = EventSerializer()
    self.index = FileIndex(root_dir)
    self.open_files = {}
    self.write_lock = Lock()

  def _get_event_file(self, ts_from):
    data_file = self.index.find_event_file(ts_from)
    if not data_file:
      try:
        self.write_lock.acquire()
        data_file = self._get_new_data_file(ts_from)
        self.index.add_file(data_file.path)
      finally:
        self.write_lock.release()
    return data_file
  
  def _open_file(self, data_file):
    return MemoryFile(name=None, path=data_file.path)
  
  def _get_new_data_file(self, ts_from):
    ts_end = ts_from + self.data_file_interval
    return DataFile(join_paths(self.root_dir, '%d-%d'%(ts_from, ts_end)), ts_from, ts_end)
  
  def save(self, event):
    # lookup file/create file
    # lock it
    # save serialized event
    # unlock
    df = self._get_event_file(ts_from)
    try:
      self.write_lock.acquire()
      if not self.open_files.get(df.path):
      self.open_files[df.path] = self._open_file(df)
      mf = self.open_files[df.path]
      mf.write(self.serializer.serialize(event))
      mf.flush()
    finally:
      self.write_lock.release()
    
    
    
    
    
