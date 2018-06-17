from theia.cli.parser import get_parent_parser


def test_get_parent_parser():
    parser = get_parent_parser(name='test', desc='unit test parser')
    
    args = parser.parse_args(args=['-v'])
    assert args.version is True
    
    args = parser.parse_args(args=['--version'])
    assert args.version is True
    
    assert args.port is not None  # must have a default value
    assert args.port == 6433
        
    args = parser.parse_args(args=['-P', '8967'])    
    assert args.port == 8967
    
    args = parser.parse_args(args=['--port', '8967'])    
    assert args.port == 8967
    
    args = parser.parse_args(args=['-H', 'localhost'])
    assert args.server_host is not None
    assert args.server_host == 'localhost'
    
    args = parser.parse_args(args=['--host', 'localhost'])
    assert args.server_host is not None
    assert args.server_host == 'localhost'
    
