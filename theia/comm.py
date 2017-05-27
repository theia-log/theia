"""
client API
server API
"""

from theia.model import EventSerializer


class CommEndpoints:
  def __init__(self, hostname, port=3500, secure=True):
    pass
  
  def add_port(self, name, porturl):
    pass
  
  def close_port(self, port):
    pass
  
  def send(self, port, data):
    pass
  
  def receive(self, port, callback, path_pattern):
    pass
  
  def on_command(self, command, callback):
    pass
  
  def reply(self, command_id, data):
    pass

class Client:
  def __init__(self, id, srv_url, hostname, port=3500):
    self.id = id
    self.serializer = EventSerializer()
    self.endpoints = CommEndpoints(hostname, port)
    self.endpoints.add_port('server', srv_url)
  
  def send_event(self, event):
    self.endpoints.send('server', self.serializer.serialize(event))
  
  def _on_command(self, command):
    pass
    



