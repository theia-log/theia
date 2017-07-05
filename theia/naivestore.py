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
from os.path import join as join_paths, basename, dirname
from os import listdir
from collections import namedtuple
import re

from theia.storeapi import EventStore
from theia.model import EventSerializer, EventParser, EOFException, Event


class SequentialEventReader:

  def __init__(self, stream, event_parser):
    self.stream = stream
    self.parser = event_parser

  def events(self):
    while True:
      try:
        yield self.parser.parse_event(self.stream)
      except EOFException:
        break

  def events_no_content(self):
    while True:
      try:
        yield self.parser.parse_event(self.stream, skip_content=True)
      except EOFException:
        break

  def curr_event(self):
    try:
      return self.parser.parse_event(self.stream)
    except EOFException:
      return None
  
  def __enter__(self):
    return self
  
  def __exit__(self):
    self.stream.close()


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
    tmpf = NamedTemporaryFile(dir=self.path, delete=False)
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
  if datafiles[0].start >= ts or datafiles[-1].end <= ts:
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
    print('_load_data_file:', fname)
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
        if ts_to and df.end > ts_to:
          break
      return found
    return None

  def find_event_file(self, ts_from):
    print(ts_from, ' in ', self.files)
    idx = binary_search(self.files, ts_from)
    if idx is not None:
      return self.files[-1]
    return None

  def add_file(self, fname):
    df = self._load_data_file(fname)
    if df:
      self.files.append(df)
      self.files = sorted(self.files, key=lambda n: n.start)


class NaiveEventStore(EventStore):

  def __init__(self, root_dir):
    self.root_dir = root_dir
    self.data_file_interval = 60 # 60 seconds
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
        self.index.add_file(basename(data_file.path))
      finally:
        self.write_lock.release()
    return data_file

  def _open_file(self, data_file):
    return MemoryFile(name=basename(data_file.path), path=dirname(data_file.path))

  def _get_new_data_file(self, ts_from):
    ts_end = ts_from + self.data_file_interval
    return DataFile(join_paths(self.root_dir, '%d-%d'%(ts_from, ts_end)), ts_from, ts_end)

  def save(self, event):
    # lookup file/create file
    # lock it
    # save serialized event
    # unlock
    df = self._get_event_file(event.timestamp)
    try:
      self.write_lock.acquire()
      if not self.open_files.get(df.path):
        self.open_files[df.path] = self._open_file(df)
      mf = self.open_files[df.path]
      mf.write(self.serializer.serialize(event))
      mf.flush()
    finally:
      self.write_lock.release()

  def search(self, ts_start, ts_end=None, flags=None, match=None, order='asc'):
    data_files = self.index.find(ts_start)
    for data_file in data_files:
      yield from self._search_data_file(data_file, ts_start, ts_end, flags, match, order=='desc')
  
  def _search_data_file(self, data_file, ts_start, ts_end, flags, match, reverse):
    if reverse:
      yield from self._match_reverse(data_file, ts_start, ts_end, flags, match)
    else:
      yield from self._match_forward(data_file, ts_start, ts_end, flags, match) 
  
  def _match_forward(self, data_file, ts_start, ts_end, flags, match):
    with self._seq_event_parser(data_file) as sqp:
      events_iter = sqp.events if match is not None else sqp.events_no_content
      
      for event in events_iter():
        if event.timestamp >= ts_start and event.timestamp <= ts_end:
          if self._match(event, flags, match):
            event.content = None
            yield event
        
  
  def _match_reverse(self, data_file, ts_start, ts_end, flags, match):
    matched = []
    for m in self._match_forward(data_file, ts_start, ts_end, flags, match):
      matched.append(m)
    for m in reversed(matched):
      yield m
    
  def _seq_event_parser(self, data_file):
    return SequentialEventParser(open(data_file.path, 'rb'), EventParser())
    
  def _matches(self, event, flags, match):
    for flag in flags:
      if not flag in event.flags:
        return False
    
    if match and not match.tolower() in event.content.tolower():
      return False
    
    return True
    
    
    
