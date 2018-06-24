"""
-----------------
theia.cli.watcher
-----------------

Theia file watcher command line interface.

"""


def get_parser(subparsers):
    """Configures the subparser for the ``watcher`` command.

    :param argparse.ArgumentParser subparser: subparser for commands.

    :returns: :class:`argparse.ArgumentParser` configured for the ``watcher`` command.
    """
    parser = subparsers.add_parser('watch', help='Watcher daemon')

    parser.add_argument('-c', '--collector-server', help='Collector server name (or IP)')
    parser.add_argument('-p', '--collector-port', default=6433, type=int, help='Collector port')
    parser.add_argument('--secure', action='store_true', help='Secure connection to collector')

    parser.add_argument('-f', '--files', nargs='*', dest='files',
                        help='List of files to watch for changes')
    parser.add_argument('-d', '--directory', nargs='*', dest='dirs',
                        help='List of directories to whose files are watched for changes')

    parser.add_argument('-t', '--tags', nargs='*', dest='tags', help='List of tags')

    return parser


def run_watcher(args):
    """Runs the watcher.

    :param argparse.Namespace args: the parsed arguments passed to the CLI.
    """
    import socket
    import asyncio
    import signal
    from theia.comm import Client
    from watchdog.observers import Observer
    from theia.watcher import SourcesDaemon

    hostname = socket.gethostname()

    loop = asyncio.get_event_loop()

    client = Client(loop=loop, host=args.collector_server,
                    port=args.collector_port, path='/event', secure=args.secure)

    client.connect()

    daemon = SourcesDaemon(observer=Observer(), client=client, tags=[hostname])

    for file_path in args.files:
        daemon.add_source(fpath=file_path, tags=args.tags)

    loop.add_signal_handler(signal.SIGHUP, loop.stop)
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.add_signal_handler(signal.SIGTERM, loop.stop)
    loop.run_forever()
    loop.close()
