import argparse


def get_parent_parser(name, desc=''):
    parser = argparse.ArgumentParser(prog=name, description=desc)

    parser.add_argument('-v', '--version',
                        help='Print program version and exit', action='store_true')
    parser.add_argument('-H', '--host', help='Hostname to bind to',
                        default='localhost', dest='server_host')
    parser.add_argument('-P', '--port', help='Listen on port', default=6433)

    return parser
