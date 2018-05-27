from theia.rdbs import RDBSEventStore, EventRecord, create_store, match_any, match_all
from theia.model import Event
from theia.storeapi import EventNotFound
import re
from datetime import datetime
from uuid import uuid4
from random import randint, shuffle

def test_match_any():
    assert match_any(re.compile('test'), ['te', 'test', 'este']) == True
    assert match_any(re.compile('.est'), ['te', 'test', 'este']) == True
    assert match_any(re.compile('no'), ['test', 'tset']) == False


def test_match_all():
    assert match_all([re.compile(r) for r in ['tag1', 'tag2']], ['tag1', 'log', 'log-web', 'tag2', 'tag17']) == True
    assert match_all([re.compile(r) for r in ['tag1', 'tag3']], ['tag1', 'log', 'log-web', 'tag2', 'tag17']) == False


def test_create_store():
    store = create_store('sqlite://', verbose=True)
    assert store is not None


def test_save_and_get_event():
    evid = str(uuid4())
    store = create_store('sqlite://', verbose=True)
    ev = Event(id=evid, timestamp=str(datetime.now().timestamp()),
                     source='/var/log/test.log', tags=['a', 'b', 'c', 'd'], content='Test Event')
    
    store.save(ev)
    
    res = store.get(evid)
    
    assert res is not None
    assert res.id == evid
    assert len(res.tags) == 4
    assert res.source == '/var/log/test.log'
    assert res.content == 'Test Event'


def test_delete_event():
    evid = str(uuid4())
    store = create_store('sqlite://', verbose=True)
    ev = Event(id=evid, timestamp=str(datetime.now().timestamp()),
                     source='/var/log/test.log', tags=['a', 'b', 'c', 'd'], content='Test Event')
    
    store.save(ev)
    
    res = store.get(evid)
    assert res is not None
    
    store.delete(evid)
    
    not_found = False
    try:
        store.get(evid)
    except EventNotFound:
        not_found = True
    
    assert not_found


def test_search():
    start = datetime.now().timestamp()
    tags = { t: 0 for t in ['t1', 't2', 't3', 't4']}
    sources = {s: 0 for s in ['src1', 'src2', 'src3', 'src4']}
    content = {c:0 for c in ['event 1', 'event 2', 'event 3']}
    
    total = 223
    
    store = create_store('sqlite://', verbose=False)
    
    def choose_from(dct):
        keys = [k for k,_ in dct.items()]
        shuffle(keys)
        return keys[:randint(1, len(dct)-1)]
    
    for i in range(0, total):
        ts = choose_from(tags)
        for t in ts:
            tags[t] += 1
        src = choose_from(sources)[0]
        sources[src] += 1
        cnt = choose_from(content)[0]
        content[cnt] += 1
        ev = Event(id=str(uuid4()),
                   timestamp=start+i,
                   tags=ts,
                   source=src,
                   content=cnt)
        store.save(ev)
    
    tag1_count = 0
    for ev in store.search(ts_start=start, flags=['t1']):
        assert 't1' in ev.tags
        tag1_count += 1
    assert tag1_count == tags['t1']
    
    content_count = 0
    for ev in store.search(ts_start=start, match='event 2'):
        assert ev.content == 'event 2'
        content_count += 1
    assert content_count == content['event 2']
    
    
    

