"""
----------------
theia.naivestore
----------------

Naive implementation of the Event Store.

This module provides an implementation of the :class:`theia.storeapi.EventStore`
that stores the events in plain-text files.

The store writes to the files atomically, so there is no danger of leaving the
files in an inconsistent state.

The files in which the store keeps the events are plain text files that contain
serialized events, encoded in UTF-8. The events are written sequentially. Plain
text is chosen so that these files can be also be read and processed by other
tools (such as grep). The events are kept in multiple files. Each file contains
about a minute worth of events - all events that happened in that one minute time
span. The name of the file is the time span: <first-event-timestamp>-<last-event-timestamp>.

The naive store requires a root directory in which to store the events. Here is
an example of usage of the store:

.. code-block:: python

    from theia.naivestore import NaiveEventStore
    from theia.model import Event
    from uuid import uuid4
    from datetime import datetime

    store = NaiveEventStore(root_dir='./data')

    timestamp = datetime.now().timestamp()

    store.save(Event(id=uuid4(),
                     source='test-example',
                     timestamp=timestamp,
                     tags=['example'],
                     content='event 1'))
    store.save(Event(id=uuid4(),
                     source='test-example',
                     timestamp=timestamp + 10,
                     tags=['example'],
                     content='event 2'))
    store.save(Event(id=uuid4(),
                     source='test-example',
                     timestamp=timestamp + 20,
                     tags=['example'],
                     content='event 3'))

    # now let's search some events

    for ev in store.search(ts_start=timestamp + 5):
        print('Found:', ev.content)

would print::

    >> Found: event 2
    >> Found: event 3

"""

from tempfile import NamedTemporaryFile
from io import BytesIO, SEEK_CUR
from threading import RLock, Thread
from shutil import move
from os.path import join as join_paths, basename, dirname
from os import listdir
from collections import namedtuple
import re
import time
from logging import getLogger
from theia.storeapi import EventStore
from theia.model import EventSerializer, EventParser, EOFException


log = getLogger(__name__)


class PeriodicTimer(Thread):
    """Timer that executes an action periodically with a given interval.

    The timer executes the action in a separate thread (as this class is a subclass of :class:`threading.Thread`). To
    run the action you must call :meth:`PeriodicTimer.start`.
    The first execution of the action is delayed by ``interval`` seconds. This timer does not call the ``action``
    callback every ``interval`` seconds, but rather waits ``interval`` seconds between after the action completes until
    the next call. So for a long running tasks, the time of call of the action may not be evenly spaced.

    You can cancel this timer by calling meth:`PeriodicTimer.cancel`.

    :param interval: ``numeric``, seconds to wait between subsequent calls to ``action`` callback.
    :param action: ``function``, the action callback. This callback takes no arguments.
    """
    def __init__(self, interval, action):
        super(PeriodicTimer, self).__init__(name='periodic-timer@%f:[%s]' % (interval, str(action)))
        self.interval = interval
        self.action = action
        self.is_running = False

    def run(self):
        """Runs the periodic timer.

        Do **not** call this function directly, but rather call :meth:`PeriodicTimer.start` to run this thread.

        To cancel the timer, call :meth:`PeriodicTimer.cancel`.
        """
        self.is_running = True

        time.sleep(self.interval)
        while self.is_running:
            try:
                self.action()
            except:
                pass
            time.sleep(self.interval)

    def cancel(self):
        """Cancels the running timer.

        The timer thread may continue running until the next cycle, then it exits.
        """
        self.is_running = False


class SequentialEventReader:
    """Reads events (:class:`theia.model.Event`) from an incoming :class:`io.BytesIO` stream.

    Uses an :class:`theia.model.EventParser` to parse the events from the incoming stream.

    Provides two ways of parsing the events:

    * Parsing the event fully - loads the header and the content of the event. See :meth:`SequentialEventReader.events`.
    * Parsing only the event header - this skips the loading of the content. Useful for not wasting performance/memory
        on loading and decoding the event content when not searching by the event content.

    This reader implements the context manager interface and can be used in ``with`` statements. For example:

    .. code-block:: python

        with SequentialEventReader(stream, parser) as reader:
            for event in reader.events():
                print(event)


    :param stream: :class:`io.BytesIO`, the incoming stream to read events from.
    :param event_parser: :class:`theia.model.EventParser`, the parser used for parsing the events from the stream.

    """
    def __init__(self, stream, event_parser):
        self.stream = stream
        self.parser = event_parser

    def events(self):
        """Reads full events from the incoming stream.

        Returns an iterator for the read events and yields :class:`theia.model.Event` as it becomes available in the
        stream.

        The iterator stops if there are no more events available in the stream or the stream closes.
        """
        while True:
            try:
                yield self._actual_read()
            except EOFException:
                break

    def events_no_content(self):
        """Reads events without content (just header) from the incoming stream.

        Returns an iterator for the read events and yields :class:`theia.model.Event` as it becomes available in the
        stream.

        Note that the ``content`` property of the :class:`theia.model.Event` will always be set to None.

        The iterator stops if there are no more events available in the stream or the stream closes.
        """
        while True:
            try:
                yield self._actual_read(skip_content=True)
            except EOFException:
                break

    def curr_event(self):
        """Reads an :class:`theia.model.Event` at the current position in the stream.

        Reads the event fully.

        Returns the :class:`theia.model.Event` at the current position of the stream or ``None`` if there are no more
        available events to be read from the stream (the stream closes).
        """
        try:
            return self._actual_read()
        except EOFException:
            return None

    def _actual_read(self, skip_content=False):
        data = self.parser.parse_event(self.stream, skip_content=skip_content)
        try:
            self.stream.seek(1, SEEK_CUR)
        except:
            pass
        return data

    def __enter__(self):
        """Implements the context-manager enter method.
        Returns a reference to itself.
        """
        return self

    def __exit__(self, *args):
        """Implements the context-manager exiting method.
        Closes the underlying stream.
        """
        self.stream.close()


class MemoryFile:
    """File-system backed in-memory buffer.

    This class wraps an :class:`io.BytesIO` buffer and backs it up with a real file in the file-system.
    The writes go to the in-memory buffer, which then can be flushed to the actual file in the file-system.

    The flushing of the buffer is atomic and consistent. The buffer is first flushed to a temporary file, then the
    system buffers are synced, and then the temporary file is renamed as the actual file.

    The instances of this class are thread-safe and can be shared between threads.

    **Limitations:** This class is not optimized for large data files as it keeps all of the file data in memory. This
    may cause a performance penalty in both speed and memory consumption when dealing with large files. In those cases
    it is better to use other memory mapped file implementations.

    :param name: ``str``, the name of the file in the file-system. This is just the filename, without the directory.
    :param path: ``str``, the directory holding the file in the file-system.
    """
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.buffer = BytesIO()
        self.lock = RLock()

    def write(self, data):
        """Write to the data to the buffer.

        This writes the data to the in-memory buffer.

        :param data: ``bytes``, the data to be written to the buffer.
        """
        try:
            self.lock.acquire()
            self.buffer.write(data)
        finally:
            self.lock.release()

    def stream(self):
        """Returns a copy of the underlying :class:`io.BytesIO` in-memory stream.
        """
        # copy the buffer
        # return the copy
        try:
            self.lock.acquire()
            return BytesIO(self.buffer.getvalue())
        finally:
            self.lock.release()

    def flush(self):
        """Writes the in-memory buffer to the file in the file-system.

        This operation is atomic and guarantees that the complete state of the buffer will be written to the file.
        The underlying file will never be left in an inconsistent state. This is achieved by first writing the entire
        buffer to a temporary file (in the same directory), flushing the system buffers, then if this succeeds, renaming
        the temporary file as the original file name.
        """
        tmpf = NamedTemporaryFile(dir=self.path, delete=False)
        try:
            self.lock.acquire()
            tmpf.write(self.buffer.getvalue())
            tmpf.flush()
            move(tmpf.name, join_paths(self.path, self.name))
        finally:
            self.lock.release()


DataFile = namedtuple('DataFile', ['path', 'start', 'end'])
"""Represents a file containing data (events) within a given time interval (from ``start`` to ``end``).
"""

DataFile.path.__doc__ = """
    ``str``, the path to the data file.
"""

DataFile.start.__doc__ = """
    ``int``, timestamp, the start of the interval. The data file does not contain any events before this timestamp.
"""

DataFile.end.__doc__ = """
    ``int``, timestamp, the end of the interval. The data file does not contain any events after this timestamp.
"""


def binary_search(datafiles, timestamp):
    """Performs a binary search in the list of datafiles, for the index of the first data file that contain events that
    happened at or after the provided timestamp.

    :param datafiles: ``list`` of :class:`DataFile`, list of datafiles **sorted** in ascending order by the start
        timestamp.
    :param timestamp: ``float``, the timestamp to serch for.

    Returns the index (``int``) of the first :class:`DataFile` in the list that contains event that occurred at or
    after the provided timestamp. Returns ``None`` if no such data file can be found.
    """
    start = 0
    end = len(datafiles) - 1
    if not datafiles:
        return None
    if datafiles[0].start > timestamp or datafiles[-1].end < timestamp:
        return None

    while True:
        mid = (end + start) // 2
        if datafiles[mid].end >= timestamp:
            end = mid
        else:
            start = mid
        if end - start <= 1:
            if datafiles[start].end >= timestamp:
                return start
            return end
    return None


class FileIndex:
    """An index of :class:`DataFile` files loaded from the given directory.

    Loads an builds an index of :class:`DataFile` files from the given directory. Each data file name must be in the
    form: ``<start>-<end>``, where ``start`` and ``end`` represent the time interval of the events in that data file.

    :class:`FileIndex` loads all data files and builds a total time span of all data files. The index exposes methods
    for locating and searching files that contain the events within a given time interval.

    :param root_dir: ``str``, the directory from which to load the data files.
    """
    def __init__(self, root_dir):
        self.root = root_dir
        self.files = self._load_files(root_dir)

    def _load_files(self, root_dir):
        files = []

        for file_name in listdir(root_dir):
            data_file = self._load_data_file(file_name)
            if data_file:
                files.append(data_file)

        files = sorted(files, key=lambda n: n.start)
        log.info('Loaded %d files to index.', len(files))
        if files:
            log.info('Spanning from %d to %d', files[0].start, files[-1].end)
        return files

    def _load_data_file(self, fname):
        if re.match(r'\d+-\d+', fname):
            start, _, end = fname.partition('-')
            start, end = int(start), int(end)
            return DataFile(path=join_paths(self.root, fname), start=start, end=end)
        return None

    def find(self, ts_from, ts_to):
        """Finds the data files that contain the events within the given interval [``ts_from``, ``ts_to``].

        The interval can be open at the end ([``ts_from``, ``Inf``]), by passing ``0`` for ``ts_to``. The interval
        cannot be open at the start.

        :param ts_from: ``float``, timestamp, find all data files containing events that have timestamp greater than or
            equal to ``ts_from``.
        :param ts_to: ``float``, timestamp, find all data files containing events that have timestamp less than or equal
            to ``ts_to``. If ``0`` or ``None`` is passed for this parameter, then the end of the time span is open,
            meaning this parameter will be ignore in the search.

        Returns a ``list`` of :class:`DataFile` files that contain the events within the given interval. Returns
        ``None`` if there are no files containing events within the given interval.
        """
        idx = binary_search(self.files, ts_from)
        if idx is None and self.files:
            if self.files[0].start >= ts_from:
                idx = 0
            elif self.files[-1].end <= ts_from:
                idx = len(self.files) - 1
        if idx is not None:
            found = []
            while idx < len(self.files):
                data_file = self.files[idx]
                if ts_to:
                    if data_file.start > ts_to:
                        break # hit the last
                if data_file.start >= ts_from or data_file.end >= ts_from:
                    found.append(data_file)

                idx += 1
            return found if found else None
        return None

    def find_event_file(self, timestamp):
        """Find the event file that contains the event with the given timestamp.

        :param timestamp: ``int``, the timestamp of the event.

        Returns the :class:`DataFile` containing the event, or ``None`` if it cannot be found.
        """
        idx = binary_search(self.files, timestamp)
        if idx is not None:
            return self.files[idx]
        return None

    def add_file(self, fname):
        """Add a data file to the :class:`FileIndex`.

        The time span will be recalculated to incorporate this new data file.

        :param fname: ``str``, the file name of the data file to be added to the file index.
        """
        data_file = self._load_data_file(fname)
        if data_file:
            self.files.append(data_file)
            self.files = sorted(self.files, key=lambda n: n.start)


class NaiveEventStore(EventStore):
    """A naive implementation of the :class:`theia.storeapi.EventStore` that keeps the event data is a plain text files.

    The events are kept in plain text files, serialized by default in UTF-8. The files are human readable and the format
    is designed to be (relatively) easily processed by other tools as well (such as ``grep``). Each data file contains
    events that happened within one minute (60000ms). The names of the data files also reflect the time span interval,
    so for example a file with name *1528631988-1528632048* contains only events that happened at or after
    ``1528631988``, but before ``1528632048``.

    The store by default uses in-memory buffers to write new events, and flushes the buffer periodically. By default
    the flushing occurs roughly every second (1000ms, see the parameter ``flush_interval``). This increases the
    performance of the store, but if outage occurs within this interval, the data in the in-memory buffers will be lost.
    The store can be configured to flush the events immediately on disk (by passing ``0`` for ``flush_interval``), but
    this decreases the performance of the store significantly.

    The instances of this class are thread-safe and can be shared between threads.

    :param root_dir: ``str``, the root directory where to store the events data files.
    :param flush_interval: ``int``, flush interval for the data files buffers in milliseconds. The event data files will
        be flushed and persisted on disk every ``flush_interval`` milliseconds. The default value is 1000ms. To flush
        immediately (no buffering), set this value equal or less than ``0``.
    """
    def __init__(self, root_dir, flush_interval=1000):
        self.root_dir = root_dir
        self.data_file_interval = 60  # 60 seconds
        self.serializer = EventSerializer()
        self.index = FileIndex(root_dir)
        self.open_files = {}
        self.write_lock = RLock()
        self.flush_interval = flush_interval  # <=0 immediate, otherwise will flush periodically
        self.timer = None
        if flush_interval > 0:
            self.timer = PeriodicTimer(flush_interval / 1000, self._flush_open_files)
            self.timer.start()
            log.info('Flushing buffers every %fms', (flush_interval / 1000))

    def _get_event_file(self, ts_from):
        data_file = self.index.find_event_file(ts_from)
        if not data_file:
            try:
                self.write_lock.acquire()
                data_file = self._get_new_data_file(ts_from)
                self.index.add_file(basename(data_file.path))
            finally:
                self.write_lock.release()
        return data_file

    def _open_file(self, data_file):
        return MemoryFile(name=basename(data_file.path), path=dirname(data_file.path))

    def _flush_open_files(self):
        for file_name, open_file in self.open_files.items():
            try:
                open_file.flush()
            except Exception as e:
                log.error('Error while flushing %s. Error: %s', file_name, e)

    def _get_new_data_file(self, ts_from):
        ts_end = ts_from + self.data_file_interval
        return DataFile(join_paths(self.root_dir, '%d-%d' % (ts_from, ts_end)), ts_from, ts_end)

    def save(self, event):
        # lookup file/create file
        # lock it
        # save serialized event
        # unlock
        data_file = self._get_event_file(event.timestamp)
        try:
            self.write_lock.acquire()
            if not self.open_files.get(data_file.path):
                self.open_files[data_file.path] = self._open_file(data_file)
            mem_file = self.open_files[data_file.path]
            mem_file.write(self.serializer.serialize(event))
            mem_file.write('\n'.encode(self.serializer.encoding))
            if self.flush_interval <= 0:
                mem_file.flush()
        finally:
            self.write_lock.release()

    def search(self, ts_start, ts_end=None, flags=None, match=None, order='asc'):
        data_files = self.index.find(ts_start, ts_end)
        if data_files:
            for data_file in data_files:
                yield from self._search_data_file(data_file, ts_start, ts_end, flags, match, order == 'desc')

    def close(self):
        self._flush_open_files()
        if self.timer:
            self.timer.cancel()
            self.timer.join()
        log.info('Naive Store stopped')

    def _search_data_file(self, data_file, ts_start, ts_end, flags, match, reverse):
        if reverse:
            yield from self._match_reverse(data_file, ts_start, ts_end, flags, match)
        else:
            yield from self._match_forward(data_file, ts_start, ts_end, flags, match)

    def _match_forward(self, data_file, ts_start, ts_end, flags, match):
        with self._seq_event_parser(data_file) as sqp:
            for event in sqp.events():
                if event.timestamp >= ts_start and (ts_end is None or event.timestamp <= ts_end):
                    if self._matches(event, flags, match):
                        yield event

    def _match_reverse(self, data_file, ts_start, ts_end, flags, match):
        matched = []
        for result in self._match_forward(data_file, ts_start, ts_end, flags, match):
            matched.append(result)
        for result in reversed(matched):
            yield result

    def _seq_event_parser(self, data_file):
        return SequentialEventReader(open(data_file.path, 'rb'), EventParser())

    def _matches(self, event, flags, match):
        if flags is not None and event.tags:
            for flag in flags:
                if not flag in event.tags:
                    return False

        if match and event.content and match:
            if not re.search(match, event.content):
                return False

        return True

    def get(self, event_id):
        """:class:`NaiveEventStore` does not support indexing, so search by ``id`` is also not supported.
        """
        log.warning('Get event by id [%s], but operation "get" is not supported in NaiveEventStore.', event_id)
        raise Exception('Get event not supported.')

    def delete(self, event_id):
        """:class:`NaiveEventStore` does not support indexing, so a delete by ``id`` is not supported.
        """
        log.warning('Delete event by id [%s], but operation "delete" is not supported in NaiveEventStore.', event_id)
        raise Exception('Delete event not supported.')
