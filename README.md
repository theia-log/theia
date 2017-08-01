# theia
Simple and lightweight log aggregator

# Introduction
Theia is a log aggregator that collects logs from multiple log files usually on multiple machines and provides the log entries on a single endpoint. 
Each recorded entry comes from a single source (log file) and can be tagged with multiple tags. This way you can query an filter by the source (for example /var/log/apache or /var/log/reds) and tags (for example "production1", "cache-server", "testing" etc), or you can just simply match a pattern against the content of the entry.

Theia has two parts:
 * watcher - this is the agent process running on the machine where you have your logs. You will have multiple watchers, but usually a single watcher per node
 * collector - this is the master process, usually running on a sperate node where you're going to collect the logs. Providesthe interface for pushing the log events and an interface for querying the aggregated logs.

# Installation

Theia comes as a single python package (only python3 is supported). 
For now you can clone this repository and install the requirements with pip.
Once it becomes available on https://pypi.python.org/ you would be able to install it via pip.

# Note
**This is still  work in progress and is far from production ready**

