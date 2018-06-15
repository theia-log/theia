from theia.watcher import FileSource
import tempfile
from unittest import mock

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
