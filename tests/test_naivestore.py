from unittest import mock
from theia.naivestore import (PeriodicTimer,
                              EOFException,
                              SequentialEventReader,
                              MemoryFile,
                              FileIndex,
                              DataFile)
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
