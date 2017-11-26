from theia.cli.parser import get_parent_parser as parent_parser
from theia.query import Query
import asyncio
import signal
from theia.model import EventParser
from io import BytesIO
from datetime import datetime


def get_parser(subparsers):
    parser = subparsers.add_parser('query', help='Query for events')

    parser.add_argument('-l', '--live', action='store_true', dest='live',
                        help='Filter events in real time (live).')

    parser.add_argument('--id', dest='f_id', metavar='PATTERN',
                        default=None, help='Filter by event id')
    parser.add_argument('-s', '--source', dest='f_source', metavar='PATTERN',
                        default=None, help='Filter by event source')
    parser.add_argument('-a', '--after', dest='f_after', metavar='TIMESTAMP',
                        default=0, type=int, help='Match events after this timestamp')
    parser.add_argument('-b', '--before', dest='f_before', metavar='TIMESTAMP',
                        default=0, type=int, help='Match events before this timestamp')
    parser.add_argument('-c', '--content', dest='f_content', metavar='PATTERN',
                        default=None, help='Match event content')
    parser.add_argument('-t', '--tags', nargs='*', dest='f_tags',
                        metavar='PATTERN', help='Match any of the tags')
    parser.add_argument('-o', '--order', dest='f_order', default='asc', metavar='ORDERING',
                        help='Order of results (asc or desc). Valid only for "find".')

    parser.add_argument('-F', '--format-output', dest='o_format', default='{timestamp:15} [{source:10}] {tags:15}: {content}',
                        metavar='FORMAT_STRING', help='Event output format string. Available properties are: id, tags, source, timestamp and content.')
    parser.add_argument('-T', '--format-timestamp', dest='o_ts_format', default='%Y-%m-%d %H:%M:%S.%f%Z',
                        metavar='DATE_FORMAT_STRING', help='Timestamp strftime compatible format string')


def format_event(ev, fmt, datefmt=None):
    dt = {
        "id": ev.id,
        "tags": ",".join(ev.tags),
        "source": ev.source,
        "content": ev.content
    }
    if datefmt:
        try:
            evt = datetime.fromtimestamp(ev.timestamp)
            dt['timestamp'] = evt.strftime(datefmt)
        except ValueError:
            dt['timestamp'] = ev.timestamp
    else:
        dt["timestamp"] = ev.timestamp

    return fmt.format(**dt)


def run_query(args):
    loop = asyncio.get_event_loop()
    query = Query(host=args.server_host, port=args.port, loop=loop)

    cf = {}
    if args.f_source:
        cf['source'] = args.f_source
    if args.f_id:
        cf['id'] = args.f_id
    if args.f_after:
        cf['start'] = args.f_after
    if args.f_before:
        cf['end'] = args.f_before
    if args.f_content:
        cf['content'] = args.f_content
    if args.f_tags:
        cf['tags'] = args.f_tags

    if not args.live:
        cf['order'] = args.f_order

    result = None
    parser = EventParser('UTF-8')

    def printev(evdata):
        if isinstance(evdata, str):
            print(evdata)
            return
        try:
            ev = parser.parse_event(BytesIO(evdata))
            print(format_event(ev, args.o_format, args.o_ts_format))
        except Exception as e:
            print('> Failed to show event', e)
            try:
                print('Value received: ', evdata.decode('UTF-8'))
            except:
                print('Raw data:', evdata)

    if args.live:
        result = query.live(cf, printev)
    else:
        result = query.find(cf, printev)

    loop.add_signal_handler(signal.SIGHUP, loop.stop)
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.add_signal_handler(signal.SIGTERM, loop.stop)
    loop.run_forever()
    loop.close()
