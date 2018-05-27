"""Relational database EventStore implementation.
"""


from theia.storeapi import EventStore, EventWriteException, EventReadException, EventNotFound, EventStoreException
from theia.model import Event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, create_engine, desc
from sqlalchemy.orm import sessionmaker
import re


Base = declarative_base()


class EventRecord(Base):
    
    __tablename__ = 'events'
    
    id = Column(String, primary_key=True)
    timestamp = Column(Float, index=True)
    tags = Column(String)
    source = Column(String, index=True)
    content = Column(String, index=True)
    custom_headers = Column(String)


class RDBSEventStore(EventStore):
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.bulk_size = 128
    
    def _session(self):
        return self.session_factory()
    
    def save(self, event):
        er = EventRecord(id=event.id,
                         timestamp=float(event.timestamp),
                         tags=','.join((event.tags or [])),
                         source=event.source,
                         content=event.content)
        sess = self._session()
        try:
            sess.add(er)
            sess.commit()
        finally:
            sess.close() 
    
    def delete(self, event_id):
        print('**********')
        sess = self._session()
        try:
            er = sess.query(EventRecord).get(event_id)
            if not er:
                raise EventNotFound()
            sess.delete(er)
            sess.commit()
            print('DELETED:', er)
        except Exception as e:
            raise EventWriteException(str(e)) from e
        finally:
            sess.close()
        
    
    def get(self, event_id):
        sess = self._session()
        try:
            er = sess.query(EventRecord).get(event_id)
            if not er:
                raise EventNotFound()
            return Event(id=er.id,
                         timestamp=str(er.timestamp),
                         tags=(er.tags or '').split(','),
                         source=er.source,
                         content=er.content)
        except EventNotFound as ne:
            raise ne
        except Exception as e:
            raise EventReadException(str(e)) from e
        finally:
            sess.close()
    
    def search(self, ts_start, ts_end=None, flags=None, match=None, order='asc'):
        if not ts_start:
            raise EventStoreException('start timestamp is required when searching events')
        
        flag_matchers = None
        content_matcher = None
        if flags and len(flags):
            try:
                flag_matchers = [re.compile(f) for f in flags]
            except Exception as e:
                raise EventStoreException('invalid flags match regex.')
        
        if match:
            try:
                content_matcher = re.compile(match)
            except Exception as e:
                raise EventStoreException('invalid content match regex.')
        
        
        def get_bulk(b):
            sess = self._session()
            q = sess.query(EventRecord).filter(EventRecord.timestamp >= ts_start)
            
            if ts_end:
                q.filter(EventRecord.timestamp <= ts_end)
            if order == 'asc':
                q.order_by(EventRecord.timestamp)
            else:
                q.order_by(desc(EventRecord.timestamp))
            
            results = []
            count = 0
            for er in q.limit(self.bulk_size).offset(b*self.bulk_size).all():
                count += 1
                flags = (er.tags or '').split(',')
                
                if flag_matchers:
                    if not match_all(flag_matchers, flags):
                        continue
                
                if content_matcher:
                    if not content_matcher.fullmatch(er.content or ''):
                        continue
                
                ev = Event(id=er.id,
                           timestamp=str(er.timestamp),
                           tags=flags,
                           source=er.source or '',
                           content=er.content)
                        
                results.append(ev)
            return results, b, count > 0
        
        page = 0
        has_more = True
        while has_more:
            results, page, has_more = get_bulk(page)
            for r in results:
                yield r
            page += 1
                
        
def match_any(matcher, values):
    for val in values:
        if matcher.fullmatch(val):
            return True
    return False


def match_all(matchers, values):
    for m in matchers:
        if not match_any(m, values):
            return False
    return True

def create_store(db_url, verbose=False):
    engine = create_engine(db_url, echo=verbose)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    
    return RDBSEventStore(session_factory)
