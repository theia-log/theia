from theia.comm import Server
from theia.model import EventParser, EventSerializer
import asyncio
from threading import Thread
from io import BytesIO
import json


class LiveFilter:
  ALLOWED_CRITERIA = {'id': str, 'source': str, 'start': int, 'end': int, 'content': str, 'tags': list}
  def __init__(self, ws, criteria):
    self.ws = ws
    self.criteria = criteria
    self._check_criteria()
  
  def _check_criteria(self):
    for k, v in self.criteria.items():
      allowed = LiveFilter.ALLOWED_CRITERIA[k]
      if allowed is None:
        raise Exception('unknown criteria %s'%k)
      if not isinstance(v, allowed):
        raise Exception('invalid value for criteria %s' % k)
  
  def match(self, event):
    return event.match(**self.criteria)


class Live:
  
  def __init__(self, serializer):
    self.serializer = serializer
    self.filters = {}
  
  def add_filter(self, f):
    self.filters[f.ws] = f
  
  async def pipe(self, event):
    for ws, f in self.filters.items():
      if f.match(event):
        try:
          result = None
          try:
            result = self.serializer.serialize(event)
          except se:
            #failed to serialize
            result = json.dumps({error: True, message: str(e)})
            print('err=', se)
          await ws.send(result)
        except e:
          print('Something went wrong', e)
        

class Collector:

  def __init__(self, store, hostname='0.0.0.0', port=4300):
    self.hostname = hostname
    self.port = port
    self.server = None
    self.store = store
    self.server_thread = None
    self.store_thread = None
    self.store_loop = None
    self.server_loop = None
    self.parser = EventParser()
    self.serializer = EventSerializer()
    self.live = Live(self.serializer)
    
    
  def run(self):
    self._setup_store()
    self._setup_server()
    self.store_thread.join()
  
  def stop(self):
    self.server.stop()
    try:
      self.store_loop.call_soon_threadsafe(self.store_loop.stop)
    finally:
      self.server_loop.call_soon_threadsafe(self.server_loop.stop)
    self.store.close()
  
  def _setup_store(self):
    def run_store_thread():
      loop = asyncio.new_event_loop()
      self.store_loop = loop
      loop.run_forever()
      loop.close()
      print('store is shut down.')
      
    self.store_thread = Thread(target=run_store_thread)
    self.store_thread.start()
  
  def _setup_server(self):
    def run_in_server_thread():
      loop = asyncio.new_event_loop()
      self.server_loop = loop
      self.server = Server(loop=loop, host=self.hostname, port=self.port)
      self.server.on_action('/event', self._on_event)
      self.server.on_action('/live', self._add_live_filter)
      self.server.on_action('/find', self._find_event)
      self.server.start()
      loop.run_forever()
      loop.close()
      print('server is shut down.')
    
    self.server_thread = Thread(target=run_in_server_thread)
    self.server_thread.start()
  
  def _on_event(self, path, message, websocket, resp):
    try:
      self.store_loop.call_soon_threadsafe(self._store_event, message)
    except Exception as e:
      print(e)
  
  def _store_event(self, message):
    event = self.parser.parse_event(BytesIO(message))
    self.store.save(event)
    try:
      asyncio.run_coroutine_threadsafe(self.live.pipe(event), self.server_loop)
    except Exception as e:
      print('Error in pipe:', e, event)
    
  def _add_live_filter(self, path, message, websocket, resp):
    criteria = json.loads(message)
    f = LiveFilter(websocket, criteria)
    self.live.add_filter(f)
    return 'ok'
  
  def _find_event(self, path, message, websocket, resp):
    criteria = json.loads(message)
    ts_from = criteria.get('start')
    ts_to = criteria.get('end')
    flags = criteria.get('tags')
    content = criteria.get('content')
    order = criteria.get('order') or 'asc'
    if not ts_from:
      raise Exception('Missing start timestamp')
    self.store_loop.call_soon_threadsafe(self._find_event_results, ts_from, ts_to, flags, content, order, websocket)
    return 'ok'
    
  def _find_event_results(self, start, end, flags, match, order, websocket):
    for ev in self.store.search(ts_start=start, ts_end=end, flags=flags, match=match, order=order):
        ser = self.serializer.serialize(ev)
        asyncio.run_coroutine_threadsafe(websocket.send(ser), self.server_loop)
    
    
