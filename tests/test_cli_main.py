from collections import namedtuple
from unittest import mock
import theia.cli.watcher
import theia.cli.collector
import theia.cli.query
import sys
import io
from theia.metadata import version
import logging
from argparse import ArgumentParser
import importlib

_Namespace = namedtuple('Namespace', ['version', 'verbose', 'command'])


@mock.patch.object(sys, 'exit')
@mock.patch('sys.stdout', new_callable=io.StringIO)
def test_cli_main_version(fake_out, m_exit):
    if 'theia.cli.__main__' in sys.modules:
        del sys.modules['theia.cli.__main__']
    m_exit.side_effect = Exception('EXIT')
    sys.argv = ['theia.py', '-v']
    try:
        globs = {}
        globs.update(globals())
        locs = {}
        locs.update(locals())
        importlib.__import__('theia.cli.__main__', globs, locs)
    except Exception as e:
        assert str(e) == 'EXIT'

    assert fake_out.getvalue() == 'theia %s\n' % version
    assert m_exit.called_once_with(0)


@mock.patch.object(logging, 'basicConfig')
def test_cli_main_verbose(m_basicConfig):
    if 'theia.cli.__main__' in sys.modules:
        del sys.modules['theia.cli.__main__']
    sys.argv = ['theia.py', '--verbose']
    
    globs = {}
    globs.update(globals())
    locs = {}
    locs.update(locals())
    
    importlib.__import__('theia.cli.__main__', globs, locs)
    
    assert m_basicConfig.call_count == 1


@mock.patch.object(theia.cli.collector, 'run_collector')
def test_cli_main_command_collector(m_run_collector):
    if 'theia.cli.__main__' in sys.modules:
        del sys.modules['theia.cli.__main__']
    sys.argv = ['theia.py', 'collect']
    globs = {}
    globs.update(globals())
    locs = {}
    locs.update(locals())
    
    importlib.__import__('theia.cli.__main__', globs, locs)
    
    assert m_run_collector.call_count == 1


@mock.patch.object(theia.cli.watcher, 'run_watcher')
def test_cli_main_command_watcher(m_run_watcher):
    if 'theia.cli.__main__' in sys.modules:
        del sys.modules['theia.cli.__main__']
    sys.argv = ['theia.py', 'watch']
    globs = {}
    globs.update(globals())
    locs = {}
    locs.update(locals())
    
    importlib.__import__('theia.cli.__main__', globs, locs)
    
    assert m_run_watcher.call_count == 1


@mock.patch.object(theia.cli.query, 'run_query')
def test_cli_main_command_watcher(m_run_query):
    if 'theia.cli.__main__' in sys.modules:
        del sys.modules['theia.cli.__main__']
    sys.argv = ['theia.py', 'query']
    globs = {}
    globs.update(globals())
    locs = {}
    locs.update(locals())
    
    importlib.__import__('theia.cli.__main__', globs, locs)
    
    assert m_run_query.call_count == 1
