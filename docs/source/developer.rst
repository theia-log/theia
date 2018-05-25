Developers Guide
================

Simulate Events
---------------

Theia comes with an events simulator script. This generates 'lorem-impsum' style
events and pushes them to a running Theia collector server.

To run the script, make sure you've activated your virtual environment, then:
    .. code-block:: javascript
        
        pip install lorem
        
        python -m theia.cli.simulate -t tag1 tag2 tag3 -s src1 src2 src3 --context-size 120

This will run the event simulator that will generate events with random subset of the 
tags (tag1, tag2 and tag3) and random subset of sources (src1, src2 and src3) with
a random content of size approximately 120 bytes (the size is randomized).

Full list of options for the simulator script:

* ``-H HOST``, ``--host HOST`` - Collector host
* ``-p PORT``, ``--port PORT`` - Collector port
* ``-t [TAGS [TAGS ...]]``- Set of tags to choose from
* ``-s [SOURCES [SOURCES ...]]`` - Set of event sources to choose from 
* ``-c CONTENT`` - Use this event content instead of random content.
* ``--content-size CONTENT_SIZE`` - Size of content (approximately)
* ``--delay DELAY`` - Delay between event in seconds

