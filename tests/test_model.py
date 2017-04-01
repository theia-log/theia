from theia.model import Event, EventSerializer

from unittest import TestCase


class TestEventSerializer(TestCase):
  
  def test_serialize_event(self):
    ev_str = EventSerializer().serialize(Event(id='id1',source='env1',content='TEST EVENT'))
    print(ev_str)