Connector Websocket API
=======================

Theia collector is the main process that aggregates events from multiple sources.
This is a WebSocket socket server that exposes endpoints for pushing and retrieving
events. When retrieving events, the client must always supply a filter.

All exposed APIs are designed as event streams - i.e you can push event at any 
time reusing the same websocket without specifying the number of events that will
be pushed. Similarly when retrieving events, you will receive the filter results
without notification of the number of total matching events. The client will receive
an event data message asynchronously - the only guarantee is that the event message
itself is consistent (you won't receive a half message, either the full event 
passes through or none of it).

The collector exposes a real-time event stream as well that pushes events that match
a certain filter criteria back to the client.

Event model
-----------

Each event is a textual message consisting of the following properties:

* ``id`` - the event ID. This value is unique across the whole system.
* ``timestamp`` - the time (and) date when the event was created. This is a UNIX-like timestamp, but may contain nanoseconds info.
* ``source`` - the source of the event. It may be the path of the log file being watched for changes, name of the sensor generating the event etc.
* ``tags`` - comma separated list of values acting as tags. Example: ``web,httpd,access-log,server1,datacenter3``
* ``content`` - the actual content of the event. Plain text.

Event Format
------------

The events are plain text strings. Here is an example of an event ::

    id:331c531d-6eb4-4fb5-84d3-ea6937b01fdd
    timestamp: 1509989630.6749051
    source:/dev/sensors/door1-sensor
    tags:sensors,home,doors,door1
    Door has been unlocked.


The basic layout of an event looks like this ::
    
    id:<id-string>
    timestamp:<unix-timestamo>.<nanos>
    source:<event-source>
    tags:<comma-separated-tags>
    <content>
    
The events are expected to be **UTF-8** encoded.

One event has two main parts: the header and the event content.
The header has at least 4 lines: **id**, **timestamp**, **source** and **tags**.
These are always present and always start with the line type then a colon **:**, 
then the header value (no empty spaces).
If the header value is empty, then only the header name will be present plus the 
colon::
    
    id:331c531d-6eb4-4fb5-84d3-ea6937b01fdd
    timestamp: 1509989630.6749051
    source:/dev/sensors/door1-sensor
    tags:
    Door has been unlocked.

Custom header fields may be added later on, but the current implementation supports
and understands only the above four headers. The custom fields are not processed
in any way, but are stored and returned to the clients. Currently the header lines
order is not guaranteed to be preserved.
Each header **MUST** be on a single line. It the client sends multiline value
for a header, the collector will accept the value up until the line end and will
ignore the rest.

The content starts after the last header and is separated by a single newline character.

Collector WebScoket API Endpoints
---------------------------------

Push Event Endpoint
^^^^^^^^^^^^^^^^^^^

Open channel to push events.

* **Path**: ``/event``
* **Params**: None
* **Message Payload**: Serialized Event string
* **Response**: None


Find events matching criteria
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Opens channel to find events that match some criteria.
The events are pushed from the collector to the client (on the incoming port of 
the web socket). The client should only post one message containing the filter 
criteria by which to match the events.
This looks up only persisted events and will not return events in real-time, only
those received **before** this channel was opened.
Once all events have been send back to the client, the collector will close the
websocket connection to the client.

The criteria message must a JSON string with the following format:
    .. code-block:: javascript
        
        {
            "start": int,
            "end": int,
            "tags": ["string regex",...],
            "content": "string regex",
            "order": "asc|desc"
        }

Where:

* ``start`` - ``int``, *optional*: match events **after** this timestamp (UNIX).
* ``end`` - ``int``, *optional*: match events **before** this timestamp (UNIX).
* ``tags`` - array of ``string``, *optional*: match the events matching any of the supplied tags. The values are processed as regular expressions.
* ``context`` - ``string`` regular expression, *optional*: match the eventa with content matching to the supplied content regex.
* ``order`` - ``string`` one of ``asc`` or ``desc``, *optinal*: sort order for the result. The sort is performed by the event timestamp. By default it returns the events in ascending order (``asc``) which means earlier events are returned first.

**Example**

Match all events after a timestamp that have a tag ``log`` on any ``web-server`` 
and contain ``[ERROR]``:

    .. code-block:: javascript
        
        {
            "start": 1527283299,
            "tags": ["log", "web-server-.+"],
            "content": ".*\[ERROR\].*"
        }


**Endpoint params**

* **Path**: ``/find``
* **Params**: None
* **Message Payload**: first message body must be Criteria JSON.
* **Response**: Event stream


Real-time event stream
^^^^^^^^^^^^^^^^^^^^^^

Opens channel to monitor for events matching a certain criteria.
The client can open a channel to the collector to monitor for incoming events
that match the client criteria. 
This endpoint will **not** lookup events in the persistent storage, but matches
only the events coming to the collector **after** the channel was opened.

The collector does not close this channel. If a timeout occurs due to inactivity,
then the client must initiate new websocket connection.

The first message sent to the collector after establishing the channel **must**
be the filter criteria object serialized as JSON string.

The criteria object has the following format:
    .. code-block:: javascript
        
        {
            "id": "string regex",
            "start": int,
            "end": int,
            "tags": ["string regex",...],
            "source": "string regex",
            "content": "string regex"
        }

Where:

* ``id`` - ``string`` regular expression, *optional*: match any event which ``id`` matches the provided regular expression.
* ``start`` - ``int``, *optional*: match events **after** this timestamp (UNIX).
* ``end`` - ``int``, *optional*: match events **before** this timestamp (UNIX).
* ``tags`` - array of ``string``, *optional*: match the events matching any of the supplied tags. The values are processed as regular expressions.
* ``source`` - ``string`` regular expression, *optional*: match any event which ``source`` matches the provided regular expression.
* ``context`` - ``string`` regular expression, *optional*: match the eventa with content matching to the supplied content regex.


**Example**

Match all events after a timestamp that have a tag ``log`` on any ``web-server`` 
and contain ``[ERROR]`` from the ``/var/log`` files (source):

    .. code-block:: javascript
        
        {
            "start": 1527283299,
            "tags": ["log", "web-server-.+"],
            "content": ".*\[ERROR\].*",
            "source": "/var/log/.+"
        }


**Endpoint params**

* **Path**: ``/live``
* **Params**: None
* **Message Payload**: first message body must be Criteria JSON.
* **Response**: Event stream


Simple event parser and serializer in JavaScript
------------------------------------------------

An event parser and serialized in JavaScript.
    .. code-block:: javascript
    
        function parseEvent(event_str) {
            let event = {}
            
            let lines = event_str.split('\n')
            
            for (var i = 0; i < lines.length; i++) {
                let line = lines[i]
                let idx = line.indexOf(':')
                if (idx < 0) {
                    break
                }
                let prop = line.slice(0, idx);
                let value = line.slice(idx+1, line.length);
                
                if (prop == 'tags') {
                    value = value.split(',').filter( t => { return t; });
                }
                
                event[prop] = value
            }
            if (i < lines.length) {
                event.content = lines.slice(i, lines.length).join('\n')
            }
            
            return event
        }

        function serializeEvent(event) {
            let event_str = ''
            let guaranteed = ['id', 'timestamp', 'source', 'tags']
            for (var i = 0; prop = guaranteed[i]; i++) {
                let value = event[prop];
                if (prop == 'tags') {
                    value = value.join(',');
                }
                event_str += prop + ':' + value + '\n';
            }
            
            for (var prop in event) {  // add custom headers
                if (!guaranteed.includes(prop) && prop != 'content') {
                    event_str += prop + ':' + event[prop] + '\n';
                }
            }
            
            event_str += event.content;
            return event_str
        }


        var event_str = ['id:331c531d-6eb4-4fb5-84d3-ea6937b01fdd',
                         'timestamp: 1509989630.6749051',
                         'source:/dev/sensors/door1-sensor',
                         'tags:sensors,home,doors,door1',
                         'x-header:somevalue',
                         'Door has been unlocked.'].join('\n')

        var event = parseEvent(event_str);
        console.log(event)
        // prints: 
        // { id: '331c531d-6eb4-4fb5-84d3-ea6937b01fdd',
        //  timestamp: ' 1509989630.6749051',
        //  source: '/dev/sensors/door1-sensor',
        //  tags: [ 'sensors', 'home', 'doors', 'door1' ],
        //  'x-header': 'somevalue',
        //  content: 'Door has been unlocked.' }


        var serialized = serializeEvent(event);
        console.log(serialized);
        // prints:
        // id:331c531d-6eb4-4fb5-84d3-ea6937b01fdd
        // timestamp: 1509989630.6749051
        // source:/dev/sensors/door1-sensor
        // tags:sensors,home,doors,door1
        // x-header:somevalue
        // Door has been unlocked.




