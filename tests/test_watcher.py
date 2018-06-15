from theia.watcher import (FileSource,
                           DirectoryEventHandler,
                           SourcesDaemon)
import tempfile
from unittest import mock
from watchdog.observers import Observer
from theia.comm import Client
import os


def test_file_source_modified():

    mock_callback = mock.MagicMock()
    file_path = None
    
    with tempfile.NamedTemporaryFile() as tmpfile:
        fs = FileSource(file_path=tmpfile.name, callback=mock_callback, tags=['a', 'b'])
        file_path = tmpfile.name
        
        tmpfile.write('test content'.encode('utf-8'))
        tmpfile.flush()
        
        fs.modified()
    
    assert fs.position > 0
    assert mock_callback.called_once_with(b'test content', file_path, ['a','b'])


def test_file_source_moved():
    
    with tempfile.NamedTemporaryFile() as tmpfile:
        fs = FileSource(file_path=tmpfile.name, callback=None)
        
        assert fs.path == tmpfile.name
        assert fs.position == 0
        
        # change the positon
        tmpfile.write('test content'.encode('utf-8'))
        tmpfile.flush()
        fs.position = len('test content'.encode('utf-8'))
        
        fs.moved('/another/location')
        
        assert fs.path == '/another/location'
        assert fs.position == len('test content'.encode('utf-8'))  # must not reset the position


def test_file_source_created():
        fs = FileSource(file_path='/fictitious', callback=None)
        
        fs.created()
        
        assert fs.position == 0


class _FakeEvent:
    
    def __init__(self, src=None, dest=None):
        self.src_path = src
        self.dest_path = dest


def test_directory_event_handler_on_moved():
    mock_handler = mock.MagicMock()
    
    dir_handler = DirectoryEventHandler({
        'moved': mock_handler
    })
    
    dir_handler.on_moved(_FakeEvent(src='a',dest='b'))
    
    assert mock_handler.called_once_with('a', 'b')


def test_directory_event_handler_on_created():
    mock_handler = mock.MagicMock()
    
    dir_handler = DirectoryEventHandler({
        'created': mock_handler
    })
    
    dir_handler.on_moved(_FakeEvent(src='a'))
    
    assert mock_handler.called_once_with('a')


def test_directory_event_handler_on_deleted():
    mock_handler = mock.MagicMock()
    
    dir_handler = DirectoryEventHandler({
        'deleted': mock_handler
    })
    
    dir_handler.on_moved(_FakeEvent(src='a'))
    
    assert mock_handler.called_once_with('a')


def test_directory_event_handler_on_modified():
    mock_handler = mock.MagicMock()
    
    dir_handler = DirectoryEventHandler({
        'modified': mock_handler
    })
    
    dir_handler.on_moved(_FakeEvent(src='a'))
    
    assert mock_handler.called_once_with('a')


@mock.patch.object(Observer, 'start')
@mock.patch.object(Observer, 'schedule')
def test_sources_daemon_add_source(m_schedule, m_start):
    
    with tempfile.TemporaryDirectory() as tmpdir:
        
        def fake_schedule(dir_handler, pdir, recursive):
            assert isinstance(dir_handler, DirectoryEventHandler)
            assert pdir == tmpdir
            assert recursive is False
        
        m_schedule.side_effect = fake_schedule
        
        sd = SourcesDaemon(observer=Observer(), client=None, tags=['a','b'])
        
        assert m_start.call_count == 1
        
        sd.add_source(fpath=os.path.join(tmpdir, 'test_source'), tags=['c'])
        
        assert m_schedule.call_count == 1
        assert len(sd.sources) == 1
        assert len(sd.sources.get(tmpdir, {})) == 1
        assert sd.sources[tmpdir].get('test_source') is not None
        assert sd.sources[tmpdir].get('test_source').tags == ['a', 'b', 'c']


@mock.patch.object(Observer, 'start')
@mock.patch.object(Observer, 'schedule')
def test_sources_daemon_add_source_then_remove_source(m_schedule, m_start):
    
    with tempfile.TemporaryDirectory() as tmpdir:
        
        def fake_schedule(dir_handler, pdir, recursive):
            assert isinstance(dir_handler, DirectoryEventHandler)
            assert pdir == tmpdir
            assert recursive is False
        
        m_schedule.side_effect = fake_schedule
        
        sd = SourcesDaemon(observer=Observer(), client=None, tags=['a','b'])
        
        assert m_start.call_count == 1
        
        sd.add_source(fpath=os.path.join(tmpdir, 'test_source'), tags=['c'])
        
        assert m_schedule.call_count == 1
        assert len(sd.sources) == 1
        assert len(sd.sources.get(tmpdir, {})) == 1
        assert sd.sources[tmpdir].get('test_source') is not None
        assert sd.sources[tmpdir].get('test_source').tags == ['a', 'b', 'c']
        
        sd.remove_source(fpath=os.path.join(tmpdir, 'test_source'))
        
        assert len(sd.sources) == 0  # remove the directory as well


@mock.patch.object(Observer, 'start')
@mock.patch.object(Observer, 'schedule')
@mock.patch.object(Client, 'send_event')
def test_sources_daemon_modified_file(m_send_event, m_schedule, m_start):
    
    with tempfile.TemporaryDirectory() as tmpdir:
        
        state = {}
        
        def fake_schedule(dir_handler, pdir, recursive):
            assert isinstance(dir_handler, DirectoryEventHandler)
            assert pdir == tmpdir
            assert recursive is False
            state[pdir] = dir_handler

        m_schedule.side_effect = fake_schedule
        
        def fake_send(event):
            assert event.content is not None
            assert event.content == state['content'].decode('utf-8')
            assert event.tags == state['tags']
        
        
        m_send_event.side_effect = fake_send
        
        client = Client(loop=None, host=None, port=None)  # just create a reference, don't connect
        
        sd = SourcesDaemon(observer=Observer(), client=client, tags=['a','b'])
        
        assert m_start.call_count == 1
        with open(os.path.join(tmpdir, 'test_source'), 'w+b') as test_source:
            sd.add_source(fpath=os.path.join(tmpdir, 'test_source'), tags=['c'])
            
            assert m_schedule.call_count == 1
            assert len(sd.sources) == 1
            assert len(sd.sources.get(tmpdir, {})) == 1
            assert sd.sources[tmpdir].get('test_source') is not None
            assert sd.sources[tmpdir].get('test_source').tags == ['a', 'b', 'c']
    
            content = 'test content'.encode('utf-8')
            state['content'] = content
            state['tags'] = ['a', 'b', 'c']
            
            test_source.write(content)
            test_source.flush()
            
            # notify the daemon by calling the handler directly
            
            fh = state[tmpdir]
            
            fh.on_modified(_FakeEvent(src=os.path.join(tmpdir, 'test_source')))
            
            assert m_send_event.call_count == 1
            
            content = 'another change'.encode('utf-8')
            state['content'] = content
            
            test_source.write(content)
            test_source.flush()
            
            fh.on_modified(_FakeEvent(src=os.path.join(tmpdir, 'test_source')))
            
            assert m_send_event.call_count == 2


@mock.patch.object(Observer, 'start')
@mock.patch.object(Observer, 'schedule')
@mock.patch.object(FileSource, 'moved')
def test_sources_daemon_moved(m_moved, m_schedule, m_start):
    
    state = {}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        
        def fake_schedule(dir_handler, pdir, recursive):
            assert isinstance(dir_handler, DirectoryEventHandler)
            assert pdir == tmpdir
            assert recursive is False
            state[pdir] = dir_handler
        
        m_schedule.side_effect = fake_schedule
        
        sd = SourcesDaemon(observer=Observer(), client=None, tags=['a','b'])
        
        assert m_start.call_count == 1
        
        sd.add_source(fpath=os.path.join(tmpdir, 'test_source'), tags=['c'])
        
        assert m_schedule.call_count == 1
        assert len(sd.sources) == 1
        assert len(sd.sources.get(tmpdir, {})) == 1
        assert sd.sources[tmpdir].get('test_source') is not None
        assert sd.sources[tmpdir].get('test_source').tags == ['a', 'b', 'c']
        
        
        fh = state[tmpdir]
        
        with tempfile.TemporaryDirectory() as otherdir:
            fh.on_moved(_FakeEvent(src=os.path.join(tmpdir, 'test_source'), dest=os.path.join(otherdir, 'source_moved')))
        
            assert m_moved.called_once_with(os.path.join(otherdir, 'source_moved'))
            
@mock.patch.object(Observer, 'start')
@mock.patch.object(Observer, 'schedule')
@mock.patch.object(FileSource, 'created')
def test_sources_daemon_created(m_created, m_schedule, m_start):
    
    state = {}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        
        def fake_schedule(dir_handler, pdir, recursive):
            assert isinstance(dir_handler, DirectoryEventHandler)
            assert pdir == tmpdir
            assert recursive is False
            state[pdir] = dir_handler
        
        m_schedule.side_effect = fake_schedule
        
        sd = SourcesDaemon(observer=Observer(), client=None, tags=['a','b'])
        
        assert m_start.call_count == 1
        
        sd.add_source(fpath=os.path.join(tmpdir, 'test_source'), tags=['c'])
        
        assert m_schedule.call_count == 1
        assert len(sd.sources) == 1
        assert len(sd.sources.get(tmpdir, {})) == 1
        assert sd.sources[tmpdir].get('test_source') is not None
        assert sd.sources[tmpdir].get('test_source').tags == ['a', 'b', 'c']
        
        
        fh = state[tmpdir]
        
        fh.on_created(_FakeEvent(src=os.path.join(tmpdir, 'test_source')))
        
        assert m_created.called_once_with(os.path.join(tmpdir, 'test_source'))


@mock.patch.object(Observer, 'start')
@mock.patch.object(Observer, 'schedule')
@mock.patch.object(FileSource, 'removed')
def test_sources_daemon_deleted(m_removed, m_schedule, m_start):
    
    state = {}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        
        def fake_schedule(dir_handler, pdir, recursive):
            assert isinstance(dir_handler, DirectoryEventHandler)
            assert pdir == tmpdir
            assert recursive is False
            state[pdir] = dir_handler
        
        m_schedule.side_effect = fake_schedule
        
        sd = SourcesDaemon(observer=Observer(), client=None, tags=['a','b'])
        
        assert m_start.call_count == 1
        
        sd.add_source(fpath=os.path.join(tmpdir, 'test_source'), tags=['c'])
        
        assert m_schedule.call_count == 1
        assert len(sd.sources) == 1
        assert len(sd.sources.get(tmpdir, {})) == 1
        assert sd.sources[tmpdir].get('test_source') is not None
        assert sd.sources[tmpdir].get('test_source').tags == ['a', 'b', 'c']
        
        
        fh = state[tmpdir]
        
        fh.on_deleted(_FakeEvent(src=os.path.join(tmpdir, 'test_source')))
        
        assert m_removed.called_once_with(os.path.join(tmpdir, 'test_source'))
