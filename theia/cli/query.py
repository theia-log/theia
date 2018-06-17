"""
---------------
theia.cli.query
---------------

Theia query command line interface.
"""
import asyncio
import signal
from io import BytesIO
from datetime import datetime

from theia.query import Query
from theia.model import EventParser



def get_parser(subparsers):
    """Configures the subparser for the ``query`` command.

    :param argparse.ArgumentParser subparser: subparser for commands.

    Returns :class:`argparse.ArgumentParser` confured for the ``query`` command.
    """
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
    parser.add_argument('-F', '--format-output', dest='o_format',
                        default='{timestamp:15} [{source:10}] {tags:15}: {content}',
                        metavar='FORMAT_STRING', help='Event output format string.' +
                        'Available properties are: id, tags, source, timestamp and content.')
    parser.add_argument('-T', '--format-timestamp', dest='o_ts_format',
                        default='%Y-%m-%d %H:%M:%S.%f%Z', metavar='DATE_FORMAT_STRING',
                        help='Timestamp strftime compatible format string')
    parser.add_argument('--close-timeout', dest='close_timeout', default=10, type=int,
                        help='Time  (in milliseconds) given to the connecting websocket to ' +
                        'actually close the connection after receiving close frame form the server. ' +
                        'The default is 10ms.')
    return parser


def format_event(event, fmt, datefmt=None):
    """Format the received event using the provided format.

    :param theia.model.Event event: the event to format.
    :param str fmt: the format string. This is compatibile with :func:`str.format`.
    :param str datefmt: alternative date format for formatiig the event timestamp.
        The format must be compatible with :func:`datetime.strftime`

    Returns the formatted event as string.
    """
    data = {
        "id": event.id,
        "tags": ",".join(event.tags),
        "source": event.source,
        "content": event.content
    }
    if datefmt:
        try:
            event_time = datetime.fromtimestamp(event.timestamp)
            data['timestamp'] = event_time.strftime(datefmt)
        except ValueError:
            data['timestamp'] = event.timestamp
    else:
        data["timestamp"] = event.timestamp

    return fmt.format(**data)


_CRITERIA_MAP = {
    'source': 'f_source',
    'id': 'f_id',
    'start': 'f_after',
    'end': 'f_before',
    'content': 'f_content',
    'tags': 'f_tags'
}


def _to_criteria(args):
    """Builds a criteria ``dict`` based on the parser arguments.
    """
    criteria = {}
    for cr_field, arg_field in _CRITERIA_MAP.items():
        if hasattr(args, arg_field) and getattr(args, arg_field):
            criteria[cr_field] = getattr(args, arg_field)
    if not args.live:
        criteria['order'] = args.f_order
    return criteria


def event_printer(event_format, time_format, parser):
    """Builds an event printer callback with the given event format and alternative
    date-time format.

    :param str event_format: the event format string.
    :param str time_format: alternative format for the event timestamp.
    :param theia.model.EventParser: event parser

    Returns event printer that takes an event data and formats is based on the
    above formats.
    """

    def print_event(evdata):
        """Formats and prints the event data.

        :param evdata: the received event data.
        """
        if isinstance(evdata, str):
            print(evdata)
            return
        try:
            event = parser.parse_event(BytesIO(evdata))
            print(format_event(event, event_format, time_format))
        except Exception as e:
            print('> Failed to show event', e)
            try:
                print('Value received: ', evdata.decode('UTF-8'))
            except:
                print('Raw data:', evdata)

    return print_event


def run_query(args):
    """Configures and runs a :class:`theia.query.Query`.

    :param argparse.Namespace args: parsed command-line arguments.
    """
    loop = asyncio.get_event_loop()
    query = Query(host=args.server_host, port=args.port, loop=loop)

    criteria_filter = _to_criteria(args)

    result = None
    parser = EventParser('UTF-8')

    if args.live:
        result = query.live(criteria_filter, event_printer(args.o_format,
                                                           args.o_ts_format,
                                                           parser))
    else:
        result = query.find(criteria_filter, event_printer(args.o_format,
                                                           args.o_ts_format,
                                                           parser))

    def clean_stop(*arg):
        """Perform a clean stop - wait a bit for the tasks on the loop to finish.
        """
        # delay the stop a bit, give it chance to actually close the loop
        loop.call_later(args.close_timeout/1000, loop.stop)

    result.when_closed(clean_stop)

    loop.add_signal_handler(signal.SIGHUP, loop.stop)
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.add_signal_handler(signal.SIGTERM, loop.stop)
    loop.run_forever()
    loop.close()
