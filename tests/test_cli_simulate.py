from theia.cli.simulate import get_parser

def test_get_parser():
    parser = get_parser()
    
    args = parser.parse_args(['-H', 'hostname'])
    assert args.host == 'hostname'
