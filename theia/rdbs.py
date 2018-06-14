"""
----------
theia.rdbs
----------

Relational database EventStore implementation.
"""
import re
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Float, create_engine, desc
from sqlalchemy.orm import sessionmaker
from theia.storeapi import (EventStore,
                            EventWriteException,
                            EventReadException,
                            EventNotFound,
                            EventStoreException)
from theia.model import Event


Base = declarative_base()


class EventRecord(Base):
    """SQLAlchemy model representing the event.
    """

    __tablename__ = 'events'

    id = Column(String, primary_key=True)
    timestamp = Column(Float, index=True)
    tags = Column(String)
    source = Column(String, index=True)
    content = Column(String, index=True)
    custom_headers = Column(String)

    def __repr__(self):
        return 'Event<%s @ %s>' % (self.id, str(self.timestamp))

    def __str__(self):
        return self.__repr__()

    def __eq__(self, obj):
        if obj is None:
            return False
        if not isinstance(obj, EventRecord):
            return False
        return self.id == obj.id

    def __hash__(self):
        return hash(self.id)


class RDBSEventStore(EventStore):
    """EventStore that persists the events in a relational database.

    The implementation relies on SQLAlchemy ORM framework.

    :param session_factory: the SQLAlchemy SessionMaker function.
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.bulk_size = 128

    def _session(self):
        """Creates new session.
        """
        return self.session_factory()

    def save(self, event):
        """Stores the event in the underlying database.

        Note that this method only does *INSERT* as the ``EventStore`` has no concept of *UPDATE* -
        each event is only added and cannot be updated. Adding the same event twice will result in
        an error.

        :param event (theia.model.Event): the event to save.

        This method does not return a value.
        """
        event_record = EventRecord(id=event.id,
                                   timestamp=float(event.timestamp),
                                   tags=','.join((event.tags or [])),
                                   source=event.source,
                                   content=event.content)
        sess = self._session()
        try:
            sess.add(event_record)
            sess.commit()
        finally:
            sess.close()

    def delete(self, event_id):
        """Deletes the event with the given event id.

        :param event_id(str): the event id
        """
        sess = self._session()
        try:
            event_record = sess.query(EventRecord).get(event_id)
            if not event_record:
                raise EventNotFound()
            sess.delete(event_record)
            sess.commit()
        except Exception as e:
            raise EventWriteException(str(e)) from e
        finally:
            sess.close()

    def get(self, event_id):
        """Looks up an event by its id.

        :param event_id(str): the event id.

        Returns a ``theia.model.Event`` if the event was found or ```theia.storeapi.EventNotFound``` if
        no such event can be found.
        """
        sess = self._session()
        try:
            event_record = sess.query(EventRecord).get(event_id)
            if not event_record:
                raise EventNotFound()
            return Event(id=event_record.id,
                         timestamp=str(event_record.timestamp),
                         tags=(event_record.tags or '').split(','),
                         source=event_record.source,
                         content=event_record.content)
        except EventNotFound as ne:
            raise ne
        except Exception as e:
            raise EventReadException(str(e)) from e
        finally:
            sess.close()

    def search(self, ts_start, ts_end=None, flags=None, match=None, order='asc'):
        """Performs a search through the stored events.

        :param ts_start(float): *required*, match all events that occured at or later than this time.
        :param ts_end(float): *optional*, match all events that occured before this time.
        :param flags(list): *optional*, list of string values (regular expressions) against which to match
        the event tags. Event matches only if *all* flags are matched against the event's tags.
        :param match(str): *optional*, match the content of an event. This is a regular expession as well.
        :param order(str): either ``asc`` or ``desc`` - sort the results ascending or descending based on the
        event timestamp.

        Returns an iterator over all matched results.
        """
        if not ts_start:
            raise EventStoreException('start timestamp is required when searching events')

        flag_matchers = None
        content_matcher = None
        if flags:
            try:
                flag_matchers = [re.compile(f) for f in flags]
            except Exception:
                raise EventStoreException('invalid flags match regex.')

        if match:
            try:
                content_matcher = re.compile(match)
            except Exception:
                raise EventStoreException('invalid content match regex.')

        def get_bulk(blk):
            """Fetch single page bulk results.
            """
            sess = self._session()
            qry = sess.query(EventRecord).filter(EventRecord.timestamp >= ts_start)

            if ts_end:
                qry.filter(EventRecord.timestamp <= ts_end)
            if order == 'asc':
                qry.order_by(EventRecord.timestamp)
            else:
                qry.order_by(desc(EventRecord.timestamp))

            results = []
            count = 0
            for event_record in qry.limit(self.bulk_size).offset(blk*self.bulk_size).all():
                count += 1
                flags = (event_record.tags or '').split(',')

                if flag_matchers:
                    if not match_all(flag_matchers, flags):
                        continue

                if content_matcher:
                    if not content_matcher.fullmatch(event_record.content or ''):
                        continue

                event = Event(id=event_record.id,
                              timestamp=str(event_record.timestamp),
                              tags=flags,
                              source=event_record.source or '',
                              content=event_record.content)

                results.append(event)
            return results, blk, count > 0

        page = 0
        has_more = True
        while has_more:
            results, page, has_more = get_bulk(page)
            for result in results:
                yield result
            page += 1

    def close(self):
        """Closes the store.

        Does nothing in this implementation.
        """
        pass

def match_any(matcher, values):
    """Check if the matcher matches *any* of the supplied values.

    :param matcher(regex pattern): compiled regular expression.
    :param values(list): list of ``str`` values to match.

    Returns ``True`` if *any* of the ``str`` values matches (fullmatch) the matcher;
    otherwise ``False``.
    """
    for val in values:
        if matcher.fullmatch(val):
            return True
    return False


def match_all(matchers, values):
    """Check if *all* matchers matchy any of the given values.

    Each matcher *must* match at least one value of the list of values.

    :param matchers(list): list of compiled regular expressions.
    :param values(list): list of ``str`` to match

    Returns ``True`` only if *all* of the matchers have matched at least one value of the provided
    list of values.
    """
    for matcher in matchers:
        if not match_any(matcher, values):
            return False
    return True

def create_store(db_url, verbose=False):
    """Creates new RDBSEventStore.

    :param db_url(str): The database URL in SQLAlchemy form.
    :param verbose(bool): ``True`` to show extended messages from the store.

    Returns RDBSEventStore object.
    """
    engine = create_engine(db_url, echo=verbose)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    return RDBSEventStore(session_factory)
