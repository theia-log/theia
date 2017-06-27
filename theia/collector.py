from theia.comm import Server
from theia.model import EventParser
import asyncio
from threaing import Thread
from io import BytesIO




class Collector:

  def __init__(self, store, hostname='0.0.0.0', port=4300):
    self.server = None
    self.store = store
    self.server_thread = None
    self.store_thread = None
    self.store_loop = None
    self.parser = EventParser()
    
    self._setup_store()
    self._setup_server()
    
  def run(self):
    self._setup_store()
    self._setup_server()
    self.store_thread.join()
  
  def stop(self):
    self.server.stop()
    # TODO: stop store loop
  
  def _setup_store(self):
    def run_store_thread():
      loop = asyncio.new_event_loop()
      self.store_loop = loop
      loop.run_forever()
      
    self.store_thread = Thread(target=run_store_thread)
    self.store_thread.start()
  
  def _setup_server(self):
    def run_in_server_thread():
      loop = asyncio.new_event_loop()
      self.server = Server(loop=loop, host=self.hostname port=self.port)
      self.server.on_action('/event', self._on_event)
      self.server.start()
      loop.run_forever()
    
    self.server_thread = Thread(target=run_in_server_thread)
    self.server_thread.start()
  
  def _on_event(self, path, message, websocket, resp):
    try:
      self.store_loop.call_soon_threadsafe(self._store_event, message)
    except Exception as e:
      print(e)
  
  def _store_event(self, message):
    event = self.parser.parse_event(BytesIO(message.encode('utf-8')))
    self.store.save(event)
      
