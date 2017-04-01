from time import time
from collections import namedtuple
from io import StringIO

Header = namedtuple('Header', ['id','source','timestamp'])
EventPreamble = namedtuple('EventPreamble', ['total','header','content'])


class Event:
  def __init__(self, id, source, timestamp=None, content=None):
    self.id = id
    self.source = source
    self.timestamp = timestamp or time() # time in nanoseconds UTC
    self.content = content or ''



class EventSerializer:
  
  def __init__(self, encoding='utf-8'):
    self.encoding = encoding
  
  def serialize(self, event):
    event_str = ''
    hdr = self._serialize_header(event)
    hdr_size = len(hdr.encode(self.encoding))
    cnt_size = len(event.content.encode(self.encoding))
    total_size = hdr_size + cnt_size
    event_str += 'event: %d %d %d\n' %(total_size, hdr_size, cnt_size)
    event_str += hdr
    event_str += event.content
    return event_str
    
  def _serialize_header(self, event):
    hdr = ''
    hdr += 'id:' + str(event.id) + '\n'
    hdr += 'timestamp:' + str(event.timestamp) + '\n'
    hdr += 'source:' + str(event.source) + '\n'
    return hdr


class EventParser:
  
  def __init__(self, encoding='utf-8'):
    self.encoding = encoding
  
  def parse_header(self, hdr_size, stream):
    bytes = stream.read(hdr_size)
    if len(bytes) != hdr_size:
      raise Exception('Invalid read size from buffer. The stream is either unreadable or corrupted.')
    hdr_str = bytes.decode(self.encoding)
    header = EventHeader()
    sio = StringIO(hdr_str)
    
    ln = sio.readline():
    while ln:
      ln = ln.strip()
      if not ln:
        raise Exception('Invalid header')
      idx = ln.index(':')
      prop = ln[0:idx]
      value = prop[idx+1:]
      if prop == 'id':
        header.id = value
      elif prop == 'timestamp':
        header.timestamp = int(timestamp)
      elif prop == 'source':
        header.source = value
      else:
        raise Exception('Unknown property in header %s' % prop)
    sio.close()
    return header
  
  def parse_preamble(self, stream):
    pstr = stream.readline()
    if pstr:
      pstr = pstr.decode(self.encoding).strip()
    if not pstr or not psrt.startswith('event:'):
      raise Exception('Invalid preamble line')
    
    values = pstr[len('event:') + 1:].split(' ')
    if len(values) != 3:
      raise Exception('Invalid preamble values')
    
    return EventPreamble(total=int(values[0]), header=int(values[1]), content=int(values[2]))
  
  def parse_event(self, stream):
    preamble = self.parse_preamble(stream)
    header = self.parse_content(preamble.header, stream)
    content = stream.read(preamble.content)
    if len(content) != preamble.content:
      raise Exception('Invalid content size. The stream is either unreadable or corrupted.')
    
    return Event(id=header.id, source=header.source, timestamp=event.timestamp, content=content)
    






