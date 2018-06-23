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

_Namespace = namedtuple('Namespace', ['version', 'verbose', 'command'])


@mock.patch.object(sys, 'exit')
@mock.patch('sys.stdout', new_callable=io.StringIO)
def test_cli_main_version(fake_out, m_exit):
    m_exit.side_effect = Exception('EXIT')
    sys.argv = ['theia.py', '-v']
    try:
        import theia.cli.__main__
    except Exception as e:
        assert str(e) == 'EXIT'

    assert fake_out.getvalue() == 'theia %s\n' % version
    assert m_exit.called_once_with(0)


@mock.patch.object(logging, 'basicConfig')
def test_cli_main_verbose(m_basicConfig):
    sys.argv = ['theia.py', '--verbose']
    
    import theia.cli.__main__
    
    assert m_basicConfig.call_count == 1


@mock.patch.object(theia.cli.collector, 'run_collector')
def test_cli_main_command_collector(m_run_collector):
    sys.argv = ['theia.py', 'collect']
    
    import theia.cli.__main__
    
    #assert m_run_collector.call_count == 1
