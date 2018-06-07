from unittest import mock
from theia.naivestore import (PeriodicTimer,
                              EOFException,
                              SequentialEventReader,
                              MemoryFile)
from theia.model import EventParser, Event
from time import sleep
from uuid import uuid4
from io import BytesIO
import tempfile
import os


def test_periodic_timer():
    mock_action = mock.MagicMock()
    
    pt = PeriodicTimer(action=mock_action, interval=0.2)
    pt.start()
    sleep(0.41)
    pt.cancel()
    pt.join()
    
    assert mock_action.call_count == 2

@mock.patch.object(EventParser, 'parse_event')
def test_sequential_event_reader_events(m_parse_event):
    state = {}
    total_events = 3
    
    def fake_parse_event(stream, skip_content):
        state['faked'] = state.get('faked', 0)
        if state['faked'] == total_events:
            raise EOFException('break')
        state['faked'] += 1
        
        return Event(id='event%d' % state['faked'], source='/source/%d' % state['faked'])
    
    m_parse_event.side_effect = fake_parse_event
    
    reader = SequentialEventReader(stream=BytesIO(), event_parser=EventParser())
    
    events = []
    for ev in reader.events():
        events.append(ev)
    
    assert len(events) == 3
    assert m_parse_event.call_count == 4


@mock.patch.object(EventParser, 'parse_event')
def test_sequential_event_reader_events_no_content(m_parse_event):
    state = {}
    total_events = 3
    
    def fake_parse_event(stream, skip_content):
        assert skip_content == True
        state['faked'] = state.get('faked', 0)
        if state['faked'] == total_events:
            raise EOFException('break')
        state['faked'] += 1
        
        return Event(id='event%d' % state['faked'], source='/source/%d' % state['faked'])
    
    m_parse_event.side_effect = fake_parse_event
    
    reader = SequentialEventReader(stream=BytesIO(), event_parser=EventParser())
    
    events = []
    for ev in reader.events_no_content():
        events.append(ev)
    
    assert len(events) == 3
    assert m_parse_event.call_count == 4


@mock.patch.object(EventParser, 'parse_event')
def test_sequential_event_reader_curr_event(m_parse_event):
    
    def fake_parse_event(stream, skip_content):
        assert skip_content is False
        return Event(id='event_zero', source='/source/_zero_event')
    
    m_parse_event.side_effect = fake_parse_event
    
    reader = SequentialEventReader(stream=BytesIO(), event_parser=EventParser())
    
    ev = reader.curr_event()
    
    assert ev is not None
    assert m_parse_event.call_count is 1


@mock.patch.object(EventParser, 'parse_event')
def test_sequential_event_reader_as_context_manager(m_parse_event):
    
    class _FakeBytesIO:
        
        def close(self):
            pass
    
    def fake_parse_event(stream, skip_content):
        assert skip_content is False
        return Event(id='event_zero', source='/source/_zero_event')
    
    m_parse_event.side_effect = fake_parse_event
    
    stream = _FakeBytesIO()
    stream.close = mock.MagicMock()
    
    with SequentialEventReader(stream=stream, event_parser=EventParser()) as reader:
        ev = reader.curr_event()
        assert ev is not None
        
    assert m_parse_event.call_count is 1
    assert stream.close.call_count is 1


def test_memory_file_write():
    with tempfile.TemporaryDirectory() as tmpdir:
        mf = MemoryFile(name='mf_test', path=tmpdir)
        mf.write(b'TEST') # in buffer
        
        assert mf.buffer is not None
        assert mf.buffer.getbuffer() == b'TEST'


def test_memory_file_stream():
    with tempfile.TemporaryDirectory() as tmpdir:
        mf = MemoryFile(name='mf_test', path=tmpdir)
        mf.write(b'TEST') # in buffer
        
        assert mf.buffer is not None
        assert isinstance(mf.stream(), BytesIO)
        assert mf.stream().getbuffer() == b'TEST'


def test_memory_file_flush():
    with tempfile.TemporaryDirectory() as tmpdir:
        mf = MemoryFile(name='mf_test', path=tmpdir)
        mf.write(b'TEST') # in buffer
        
        mf.flush()
        
        with open(tmpdir + os.sep + 'mf_test', 'r') as f:
            assert f.read() == 'TEST'
        
