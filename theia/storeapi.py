"""
--------------
theia.storeapi
--------------

Event Store API
^^^^^^^^^^^^^^^

Defines classes, methods and exceptions to be used when implementing an Event Store.
"""
from abc import abstractmethod


class EventStore:
    """EventStore is the basic interface for interaction with the events.

    Main uses of this store are CRUD interactions with the events. The API
    provides powerful search through all events based on a time range and
    optionally additional flags.
    An instance of this class is thread-safe.
    """
    @abstractmethod
    def save(self, event):
        """Saves an event in the underlying storage.

        This method is guaranteed to be atomic in the sense that the storage will
        either succeed to write and flush the event, or it will fail completely. In
        either case, the storage will be left in a consistent state.

        :param event: :class:`theia.model.Event`, the Event object to store.

        This method does not return any value.
        """
        pass

    @abstractmethod
    def delete(self, event_id):
        """Deletes an event from the storage.

        The delete operation removes an event from the underlying storage. This
        operation is guaranteed to be atomic, the event will either be removed or
        it will fail completely. In either case the storage will be left in a
        consistent state.

        :param event_id: ``str``, the unique identifier of the event to be removed.

        This method does not return any value.
        """
        pass

    @abstractmethod
    def get(self, event_id):
        """Looks up an event by its unique identifier.

        The storage will try to look up the event with the specified id:

        * if the event is found, it will return an Event object
        * the event is not found, raises an EventNotFound excepton.

        Edge cases:

        * If the event is being inserted AFTER the get(..) operation is invoked,
            there is NO guarantee that it will be fetched.
        * If the event is being inserted BEFORE the get(..)  operation is invoked,
            but that transaction is still not commited, the operaton will block
            until the write operation completes (or errors out) and the Event will
            be returned (if the write succeds) or will error out (if the write
            fails) - strict consistency

        **Note:**
            Some specific implementations may break the strict consistency if the
            underlying mechanism does not provide means to implement it. In those
            cases, the subclass must override this documentation and must document
            its exact for the above edge-cases.

        :param event_id: ``str``, the unique identifier of the event to be looked up.

        Returns the :class:`theia.model.Event` with the given id, or ``None`` if no such
        event exists.
        """
        pass

    @abstractmethod
    def search(self, ts_start, ts_end=None, flags=None, match=None, order='asc'):
        """Performs a search for events matching events in the specified time range.

        :param ts_start: ``float``, start of the time range. Matching events with timestamp bigger
            or equal to this paramter will be returned.
        :param ts_end: ``float``, end of the time range. Matching events with timestamp smaller or
            equal to this paramter will be returned.
        :param flags: ``list``,  events that have ALL of the flags will be returned.
        :param match: ``str``, regular expression, (restricted to a subset of the full regexp
            support) to match the event content against.
        :param order: ``str``, ``'asc'`` or ``'desc'``, order in which the events are returned.

        The operation returns an iterator over the matched (ordered) set of events.
        This operation satisfies the strict consistency.
        """
        pass

    @abstractmethod
    def close(self):
        """Close and cleanup the underlying store.
        """
        pass


class EventStoreException(Exception):
    """General store error.
    """
    pass


class EventWriteException(EventStoreException):
    """Represents an error while writing an event to the underlying storage.
    """
    pass


class EventReadException(EventStoreException):
    """Represents an error while reading an event from the underlying storage.
    """
    pass


class EventNotFound(EventReadException):
    """Raised if there is no event found in the underlying storage.
    """
    pass
