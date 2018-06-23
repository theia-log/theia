from theia.cli.watcher import get_parser, run_watcher
from unittest import mock
from argparse import ArgumentParser


def test_get_parser():
    parent_parser = ArgumentParser(prog='test')
    
    subparsers = parent_parser.add_subparsers(dest='command', title='command',
                                              help='CLI commands')
    
    parser = get_parser(subparsers)
    
    args = parser.parse_args([])
    
    assert args.collector_port == 6433
    assert args.secure is False
    
    args = parser.parse_args(['-c', 'collector_server_url'])
    assert args.collector_server == 'collector_server_url'
    
    args = parser.parse_args(['--collector-server', 'collector_server_url'])
    assert args.collector_server == 'collector_server_url'
    
    args = parser.parse_args(['-p', '11223'])
    assert args.collector_port == 11223
    
    args = parser.parse_args(['--collector-port', '11223'])
    assert args.collector_port == 11223
    
    args = parser.parse_args(['-f', 'f1', 'f2', 'f3'])
    assert args.files == ['f1', 'f2', 'f3']
    
    args = parser.parse_args(['--files', 'f1', 'f2', 'f3'])
    assert args.files == ['f1', 'f2', 'f3']
    
    args = parser.parse_args(['-d', 'd1', 'd2', 'd3'])
    assert args.dirs == ['d1', 'd2', 'd3']
    
    args = parser.parse_args(['--directory', 'd1', 'd2', 'd3'])
    assert args.dirs == ['d1', 'd2', 'd3']
    
    args = parser.parse_args(['-t', 't1', 't2', 't3'])
    assert args.tags == ['t1', 't2', 't3']
    
    args = parser.parse_args(['--tags', 't1', 't2', 't3'])
    assert args.tags == ['t1', 't2', 't3']


