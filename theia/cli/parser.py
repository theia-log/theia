"""
----------------
theia.cli.parser
----------------


Theia CLI main :mod:`argparse` parser.
"""
import argparse


def get_parent_parser(name, desc=''):
    """Creates the main (parent) :class:`argparse.ArgumentParser` for Theia CLI.

    Defines the main argument options such as theia server host, port, verbosity
    level etc.

    :param str name: the name of the program.
    :param str desc: program description.

    Returns the configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(prog=name, description=desc)

    parser.add_argument('-v', '--version',
                        help='Print program version and exit', action='store_true')
    parser.add_argument('-H', '--host', help='Hostname to bind to',
                        default='localhost', dest='server_host')
    parser.add_argument('-P', '--port', help='Listen on port', default=6433,
                        type=int)

    parser.add_argument('--verbose', dest='verbose', action='store_true',
                        help='Verbose output.')

    return parser
