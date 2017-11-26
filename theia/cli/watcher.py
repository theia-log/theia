from theia.cli.parser import get_parent_parser as parent_parser


def get_parser(subparsers):
    parser = subparsers.add_parser('watch', help='Watcher daemon')

    parser.add_argument('-c', '--collector-server', help='Collector server name (or IP)')
    parser.add_argument('-p', '--collector-port', default=6433, help='Collector port')
    parser.add_argument('--secure', action='store_true', help='Secure connection to collector')

    parser.add_argument('-f', '--files', nargs='*', dest='files',
                        help='List of files to watch for changes')
    parser.add_argument('-d', '--directory', nargs='*', dest='dirs',
                        help='List of directories to whose files are watched for changes')

    parser.add_argument('-t', '--tags', nargs='*', dest='tags', help='List of tags')

    return parser


def run_watcher(args):
    import socket
    import asyncio
    import functools
    import signal
    from theia.comm import Server, Client
    from watchdog.observers import Observer
    from theia.watcher import SourcesDaemon

    from threading import Thread

    hostname = socket.gethostname()
    print(hostname)

    loop = asyncio.get_event_loop()

    client = Client(loop=loop, host=args.collector_server,
                    port=args.collector_port, path='/event', secure=args.secure)

    client.connect()

    daemon = SourcesDaemon(observer=Observer(), client=client, tags=[hostname])

    for f in args.files:
        daemon.add_source(fpath=f, tags=args.tags)

    loop.add_signal_handler(signal.SIGHUP, loop.stop)
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.add_signal_handler(signal.SIGTERM, loop.stop)
    loop.run_forever()
    loop.close()
    print("Watcher stopped")
