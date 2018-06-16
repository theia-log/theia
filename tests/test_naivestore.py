from unittest import mock
from theia.naivestore import (PeriodicTimer,
                              EOFException,
                              SequentialEventReader,
                              MemoryFile,
                              FileIndex,
                              DataFile,
                              NaiveEventStore)
from theia.model import EventParser, Event, EventSerializer
from time import sleep
from uuid import uuid4
from io import BytesIO
import tempfile
import os


def test_periodic_timer():
    mock_action = mock.MagicMock()
    
    pt = PeriodicTimer(action=mock_action, interval=0.2)
    pt.start()
    sleep(0.5)
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


@mock.patch.object(FileIndex, '_load_files')
def test_file_index_find(m_load_files):
    # span: [10, 39]
    data_files = [DataFile(path='/file1', start=10, end=19),
                  DataFile(path='/file2', start=20, end=25),
                  DataFile(path='/file3', start=30, end=39)]
    
    def fake_load_files(root_dir):
        return data_files
    
    m_load_files.side_effect = fake_load_files
    
    file_index = FileIndex(root_dir='/tmp/fake')
    
    # right inside the span, return all
    result = file_index.find(ts_from=15, ts_to=33)
    
    assert result is not None
    assert len(result) == 3
    assert result[0].path == '/file1'
    assert result[1].path == '/file2'
    assert result[2].path == '/file3'
    
    # match first half
    
    result = file_index.find(ts_from=10, ts_to=25)
    
    assert result is not None
    assert len(result) == 2
    assert result[0].path == '/file1'
    assert result[1].path == '/file2'
    
    # match second half
    
    result = file_index.find(ts_from=25, ts_to=39)
    
    assert result is not None
    assert len(result) == 2
    assert result[0].path == '/file2'
    assert result[1].path == '/file3'
    
    # match outside boundaries
    
    result = file_index.find(ts_from=5, ts_to=105)
    
    assert result is not None
    assert len(result) == 3
    assert result[0].path == '/file1'
    assert result[1].path == '/file2'
    assert result[2].path == '/file3'
    
    # match without end boundary - all
    
    result = file_index.find(ts_from=5, ts_to=0)
    
    assert result is not None
    assert len(result) == 3
    assert result[0].path == '/file1'
    assert result[1].path == '/file2'
    assert result[2].path == '/file3'
    
    # match without end boundary - only the last
    
    result = file_index.find(ts_from=27, ts_to=0)
    
    assert result is not None
    assert len(result) == 1
    assert result[0].path == '/file3'
    
    # match without end boundary - half
    
    result = file_index.find(ts_from=21, ts_to=0)
    
    assert result is not None
    assert len(result) == 2
    assert result[0].path == '/file2'
    assert result[1].path == '/file3'
    
    # edge case: match in the gap (25, 30)
    
    result = file_index.find(ts_from=26, ts_to=29)
    
    assert result is None
    
    # edge case: match ts_to to start of first file
    result = file_index.find(ts_from=3, ts_to=10)
    
    assert result is not None
    assert len(result) == 1
    assert result[0].path == '/file1'
    
    # edge case: match ts_start to the end of the last file
    
    result = file_index.find(ts_from=39, ts_to=100)
    
    assert result is not None
    assert len(result) == 1
    assert result[0].path == '/file3'
    
    
    # match none
    
    result = file_index.find(ts_from=1000, ts_to=2000)
    
    assert result is None


@mock.patch.object(FileIndex, '_load_files')
def test_file_index_find_event_file(m_load_files):
    # span: [10, 39]
    data_files = [DataFile(path='/file1', start=10, end=19),
                  DataFile(path='/file2', start=20, end=25),
                  DataFile(path='/file3', start=30, end=39)]
    
    def fake_load_files(root_dir):
        return data_files
    
    m_load_files.side_effect = fake_load_files
    
    file_index = FileIndex(root_dir='/tmp/fake')
    
    result = file_index.find_event_file(0)
    assert result is None
    
    result = file_index.find_event_file(10)
    assert result is not None
    assert result.path == '/file1'
    
    
    result = file_index.find_event_file(13)
    assert result is not None
    assert result.path == '/file1'
    
    result = file_index.find_event_file(19)
    assert result is not None
    assert result.path == '/file1'
    
    result = file_index.find_event_file(27) # start in the gap, fetch next
    assert result is not None
    assert result.path == '/file3'
    
    result = file_index.find_event_file(23)
    assert result is not None
    assert result.path == '/file2'
    
    result = file_index.find_event_file(39)
    assert result is not None
    assert result.path == '/file3'


@mock.patch.object(FileIndex, '_load_files')
@mock.patch.object(FileIndex, '_load_data_file')
def test_file_index_add_file(m_load_data_file, m_load_files):
    # span: [10, 39]
    data_files = [DataFile(path='/file1', start=10, end=19),
                  DataFile(path='/file2', start=20, end=25),
                  DataFile(path='/file3', start=30, end=39)]
    
    def fake_load_files(root_dir):
        return data_files
    
    m_load_files.side_effect = fake_load_files
    
    
    def fake_load_data_file(path):
        return DataFile(path, start=26, end=29) # fill the gap
    
    m_load_data_file.side_effect = fake_load_data_file
    
    file_index = FileIndex(root_dir='/tmp/fake')
    
    assert file_index.files is not None
    assert len(file_index.files) == 3
    
    file_index.add_file('/file4')
    assert file_index.files is not None
    assert len(file_index.files) == 4
    assert file_index.files[0].path == '/file1'
    assert file_index.files[1].path == '/file2'
    assert file_index.files[2].path == '/file4' # the new one
    assert file_index.files[3].path == '/file3'


def test_file_index_load_files():
    def fcreate(tmpdir, name):
        with open(tmpdir + os.sep + name, 'w') as f:
            f.write('I am a test file. If you can read this, remove me.')

    with tempfile.TemporaryDirectory() as tmpdir:
        fcreate(tmpdir, '10-19')
        fcreate(tmpdir, '20-25')
        fcreate(tmpdir, '30-39')
        
        file_index = FileIndex(root_dir=tmpdir)
        
        assert file_index.files is not None
        assert len(file_index.files) == 3
        assert file_index.files[0].start == 10
        assert file_index.files[0].end == 19
        assert file_index.files[1].start == 20
        assert file_index.files[1].end == 25
        assert file_index.files[2].start == 30
        assert file_index.files[2].end == 39



def test_naive_store_save_no_buffering():
    with tempfile.TemporaryDirectory() as tmpdir:
        ns = None
        try:
            ns = NaiveEventStore(root_dir=tmpdir, flush_interval=0)
            event = Event(id='event-1', timestamp=10, source='/source/1', tags=['event', 'test'], content='event 1')
            
            ns.save(event)
            
            assert os.path.isfile(os.path.join(tmpdir, '10-70'))
            
            with open(os.path.join(tmpdir, '10-70')) as ef:
                ser_event = ef.read()
                assert ser_event == 'event: 73 66 7\nid:event-1\ntimestamp: 10.0000000\nsource:/source/1\ntags:event,test\nevent 1\n\n'
        finally:
            if ns:
                ns.close()


def test_naive_store_save_buffered():
    with tempfile.TemporaryDirectory() as tmpdir:
        ns = None
        try:
            ns = NaiveEventStore(root_dir=tmpdir, flush_interval=500)
            
            event = Event(id='event-1', timestamp=10, source='/source/1', tags=['event', 'test'], content='event 1')
            
            ns.save(event)
            
            assert os.path.isfile(os.path.join(tmpdir, '10-70')) is False
            
            sleep(0.6)
            
            assert os.path.isfile(os.path.join(tmpdir, '10-70'))
            
            with open(os.path.join(tmpdir, '10-70')) as ef:
                ser_event = ef.read()
                assert ser_event == 'event: 73 66 7\nid:event-1\ntimestamp: 10.0000000\nsource:/source/1\ntags:event,test\nevent 1\n\n'
        finally:
            if ns:
                ns.close()


def test_naive_store_search():
    known_events = [{"name": "10-70", "events": [Event(id="event-1", timestamp=10, source="/src/1", tags=["a"], content="event-1, data file 1"),
                                                 Event(id="event-2", timestamp=15, source="/src/2", tags=["b"], content="event-2, data file 1"),
                                                 Event(id="event-3", timestamp=30, source="/src/1", tags=["a", "b"], content="event-3, data file 1"),
                                                 Event(id="event-4", timestamp=67, source="/src/3", tags=["c" ], content="event-4, data file 1")]},
                    {"name": "71-131", "events": [Event(id="event-5", timestamp=75, source="/src/1", tags=["d"], content="event-5, data file 2"),
                                                  Event(id="event-6", timestamp=100, source="/src/4", tags=["e" ], content="event-6, data file 2")]},
                    {"name": "200-260", "events": [Event(id="event-7", timestamp=200, source="/src/5", tags=["f"], content="event-7, data file 3"),
                                                   Event(id="event-8", timestamp=210, source="/src/2", tags=["g"], content="event-8, data file 3"),
                                                   Event(id="event-9", timestamp=220, source="/src/1", tags=["h", "f"], content="event-9, data file 3"),
                                                   Event(id="event-10", timestamp=250, source="/src/6", tags=["i" ], content="event-10, data file 3")]}]
    
    serializer = EventSerializer()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # create data files with events
        for df_spec in known_events:
            with open(os.path.join(tmpdir, df_spec["name"]), "wb") as df:
                for event in df_spec["events"]:
                    df.write(serializer.serialize(event))
                    df.write("\n".encode("utf-8")) # the extra newline to separate events in the data file
        
        ns = NaiveEventStore(root_dir=tmpdir)
        try:
            # lookup all
            results = []
            for event in ns.search(ts_start=10):
                results.append(event)
            
            assert len(results) == 10
            
            # lookup in an interval
            
            results = []
            for event in ns.search(ts_start=30, ts_end=80):
                results.append(event)
            
            assert len(results) == 3
            assert [e.id for e in results] == ['event-3', 'event-4', 'event-5']
            
            # lookup by tags
            
            results = []
            for event in ns.search(ts_start=5, flags=["a"]):
                results.append(event)
            
            assert len(results) == 2
            assert [e.id for e in results] == ['event-1', 'event-3']
            
            # lookup by content
            
            results = []
            for event in ns.search(ts_start=5, match='data file 3'):
                results.append(event)
            
            assert len(results) == 4
            assert [e.id for e in results] == ['event-7', 'event-8', 'event-9', 'event-10']
            
            # lookup by content - regex through multiple files
            
            results = []
            for event in ns.search(ts_start=5, match='event-(4|5|7|10)'):
                results.append(event)
            
            assert len(results) == 4
            assert [e.id for e in results] == ['event-4', 'event-5', 'event-7', 'event-10']
        
        
        finally:
            if ns:
                ns.close()


