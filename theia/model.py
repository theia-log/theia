"""
-----------------
Theia Event Model
-----------------

Basic model of an Event, serializers and parsers for Event manipulation.
"""

from time import time
from collections import namedtuple
from io import StringIO, SEEK_CUR
import re


EventPreamble = namedtuple('EventPreamble', ['total', 'header', 'content'])


class Header:
    """Header represents an Event header. The header contains the following
    properties:

    * ``id``, unique identifier for the event. Usually UUIDv4.
    * ``timestamp``, floating point of the number of milliseconds since epoch
      start (1970-1-1T00:00:00.00).
    * ``source``, string, the name of the event source.
    * ``tags``, list of strings, arbitrary tags attached to the event.

    The header is usefull and usually used when serializing/parsing an event.
    """

    def __init__(self, id=None, timestamp=None, source=None, tags=None):
        self.id = id
        self.timestamp = timestamp
        self.source = source
        self.tags = tags


class Event:
    """Event represnts some event occuring at a specfic time.

    Each event is uniquely identified by its ``id`` in the whole system. An event
    comes from a ``source`` and always has an associated ``timestamp``. The
    timestamp is usually generated by the event producer.

    The *content* of an event is an arbitrary string. It may be a log file line,
    some generated record, readings from a sensor or other non-structured or
    structured text.

    Each event may have a list of ``tags`` associcated with it. These are arbitrary
    strings and help in filtering the events.

    An event may look like this ::

        id:331c531d-6eb4-4fb5-84d3-ea6937b01fdd
        timestamp: 1509989630.6749051
        source:/dev/sensors/door1-sensor
        tags:sensors,home,doors,door1
        Door has been unlocked.

    The constructor takes multiple arguments, of which only the id and source are
    required.

    :param id: ``str``, the event unique identifier. Must be system-wide unique. An
        UUID version 4 (random UUID) would be a good choice for ``id``.
    :param source: ``str``, the source of the event. It usually is the name of the
        monitored file, but if the event does not originate from a file, it should be
        set to the name of the proecss/system/entity that generated the event.
    :param timestamp: ``float``, time when the event occured in seconds (like UNIX
        time). The value is a floating point number with nanoseconds precission. If
        no value is given, then the current time will be used.
    :param tags: ``list``, list of ``str`` tags to add to this event.
    :param content: ``str``, the actual content of the event. The content may have
        an arbitrary lenght (or none at all).

    """

    def __init__(self, id, source, timestamp=None, tags=None, content=None):
        self.id = id
        self.source = source
        self.timestamp = timestamp or time()  # time in nanoseconds UTC
        self.tags = tags or []
        self.content = content or ''

    def match(self, id=None, source=None, start=None, end=None, content=None, tags=None):
        """Check if this event matches the provided criteria.

        The event will match only if **all** criteria is statisfied. Calling match
        without any criteria, yields ``True``.

        The criteria is processed as a regular expression. Each value is first
        converted to string, then matched against the provided regular expression -
        see :func:`re.match`. The exception of this rule are the criteria for
        ``start`` and ``end`` wich expect numeric values, as they operate on the
        :class:`Event` timestamp.

        :param id: ``str``, regular expression against which to match the :class:`Event`
            ``id``.
        :param source: ``str``, regular expression against which to match the :class:`Event`
            ``source``.
        :param start: ``float`` or ``int``, match true if the :class:`Event` timestamp
            is greater than or equal to this value.
        :param start: ``float`` or ``int``, match true if the :class:`Event` timestamp
            is less than or equal to this value.
        :param content: ``str``, regular expression against which to match the :class:`Event`
            ``content``.
        :param tags: ``list``, list of ``str`` regular expressions against which to
            match the :class:`Event` tags. Matches true only if **all** of the provided
            criteria match the Event tags.

        Returns ``True`` if this :class:`Event` matches the criteria, otherwise ``False``.
        """
        return all([self._match_header_id_and_source(id, source),
                   self._match_timestamp(start, end),
                   self._match_tags(tags),
                   self._match_content(content)])

    def _match_header_id_and_source(self, id, source):
        matches = True
        if id is not None:
            matches = _match(id, self.id)
        if matches and source is not None:
            matches = _match(source, self.source)
        return matches

    def _match_timestamp(self, start, end):
        matches = True
        if self.timestamp:
            if start is not None:
                matches = self.timestamp >= start
            if matches and end is not None:
                matches = self.timestamp <= end
        return matches

    def _match_tags(self, tags):
        if tags:
            for tag in tags:
                if tag not in self.tags:
                    return False
        return True

    def _match_content(self, content):
        if not content:
            return True
        return _match(content, self.content)


def _match(pattern, value):
    """Match the value against a regular expression pattern.
    """
    if value is None:
        return False
    return re.match(pattern, value) is not None


class EventSerializer:
    """Serialized for instances of type :class:`Event`.

    This serializes the :class:`Event` in a plain text representation of the Event.
    The serialized text is encoded in UTF-8 and the actual ``bytes`` are returned.

    The representation consists of three parts: heading, header and content.
    The heading is the first line of every event and has this format:

        event: <total_size> <header_size> <content_size>

    where:
    * ``total_size`` is the total size of the Event (after the heading) in bytes.
    * ``header_size`` is the size of the header in bytes.
    * ``content_size`` is the size of the content (after the Header) in bytes.

    The header holds the values for the Event's id, source, tags and timestamp.
    Each value is serialized on a single line. The line starts with the name of
    the property, separated by a colon(``:``), then the property value.

    The content starts after the final header and is separated by a newline.

    Here is an example of a fully serialized :class:`Event`:

        event: 155 133 22
        id:331c531d-6eb4-4fb5-84d3-ea6937b01fdd
        timestamp: 1509989630.6749051
        source:/dev/sensors/door1-sensor
        tags:sensors,home,doors,door1
        Door has been unlocked

    """
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding

    def serialize(self, event):
        event_str = ''
        hdr = self._serialize_header(event)
        hdr_size = len(hdr.encode(self.encoding))
        cnt = event.content or ''
        cnt_size = len(cnt.encode(self.encoding))
        total_size = hdr_size + cnt_size
        event_str += 'event: %d %d %d\n' % (total_size, hdr_size, cnt_size)
        event_str += hdr
        event_str += cnt
        event_str += '\n'
        return event_str.encode(self.encoding)

    def _serialize_header(self, event):
        hdr = ''
        hdr += 'id:' + str(event.id) + '\n'
        hdr += 'timestamp: %.7f' % event.timestamp + '\n'
        hdr += 'source:' + str(event.source) + '\n'
        hdr += 'tags:' + ','.join(event.tags) + '\n'
        return hdr


class EventParser:

    def __init__(self, encoding='utf-8'):
        self.encoding = encoding

    def parse_header(self, hdr_size, stream):
        hbytes = stream.read(hdr_size)
        if len(hbytes) != hdr_size:
            raise Exception('Invalid read size from buffer. The stream is either unreadable \
                             or corrupted. %d read, expected %d' % (len(hbytes), hdr_size))
        hdr_str = hbytes.decode(self.encoding)
        header = Header()
        sio = StringIO(hdr_str)

        line = sio.readline()
        while line:
            line = line.strip()
            if not line:
                raise Exception('Invalid header')
            idx = line.index(':')
            prop = line[0:idx]
            value = line[idx + 1:]
            if prop == 'id':
                header.id = value
            elif prop == 'timestamp':
                header.timestamp = float(value)
            elif prop == 'source':
                header.source = value
            elif prop == 'tags':
                header.tags = value.split(',')
            else:
                raise Exception('Unknown property in header %s' % prop)
            line = sio.readline()
        sio.close()
        return header

    def parse_preamble(self, stream):
        pstr = stream.readline()
        if not pstr:
            raise EOFException()
        if pstr:
            pstr = pstr.decode(self.encoding).strip()

        if not pstr.startswith('event:'):
            raise Exception('Invalid preamble line: [%s]' % pstr)

        values = pstr[len('event:') + 1:].split(' ')
        if len(values) != 3:
            raise Exception('Invalid preamble values')

        return EventPreamble(total=int(values[0]), header=int(values[1]), content=int(values[2]))

    def parse_event(self, stream, skip_content=False):
        preamble = self.parse_preamble(stream)
        header = self.parse_header(preamble.header, stream)
        content = None
        if skip_content:
            stream.seek(preamble.content, SEEK_CUR)
        else:
            content = stream.read(preamble.content)
            content = content.decode(self.encoding)

        stream.seek(1, SEEK_CUR)  # new line after each event

        if not skip_content and len(content) != preamble.content:
            raise Exception('Invalid content size. The stream is either unreadable or corrupted.')

        return Event(id=header.id, source=header.source, timestamp=header.timestamp,
                     tags=header.tags, content=content)


class EOFException(Exception):
    pass
