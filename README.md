# theia
Simple and lightweight log aggregator

# Introduction
Theia is a log aggregator that collects logs from multiple log files usually on multiple machines and provides the log entries on a single endpoint. 
Each recorded entry comes from a single source (log file) and can be tagged with multiple tags. This way you can query an filter by the source (for example /var/log/apache or /var/log/reds) and tags (for example "production1", "cache-server", "testing" etc), or you can just simply match a pattern against the content of the entry.

Theia has three parts:
 * watcher - this is the agent process running on the machine where you have your logs. You will have multiple watchers, but usually a single watcher per node
 * collector - this is the master process, usually running on a sperate node where you're going to collect the logs. Provides the interface for pushing the log events and an interface for querying the aggregated logs.
 * client - client for querying and watching live events. This connects to the collector via websocket and
queries the collected events or registers a filter for live events.

# Installation

Theia comes as a single python package (only python3 is supported). 

With ```pip```:
```bash
pip install theia
```

# Running the collector

This process collects and stores the events. The built-in database uses text files to store the events.

Create a directory where you want to keep the events, and run the collector server:

```bash
mkdir data

python -m theia.cli collect -d ./data

```

This will run the server listening on port ```6433```.

# Running a watcher

Make sure you have the collector running.

Then, run the watcher:

```bash
python -m theia.cli watch -c localhost -f /var/log/httpd/access.log -t web-access
```

This would watch for changes in ```access.log``` and send events to the collector 
tagged with ```web-access```

# Run a query

To query for all log events with tag ```web-access```:

```bash
python -m theia.cli query -c localhost -t web-access
```

# Run a live filter

To watch the events with tag ```web-access``` as they arrive in real-time:

```bash
python -m theia.cli query -l -c localhost -t web-access
```

# Note
**This is still  work in progress and is far from production ready**

