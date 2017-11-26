import asyncio
from theia.comm import Client
import json


class resultHandler:

    def __init__(self, client, on_close=None):
        self.client = client
        self.on_close = on_close

    def close(self):
        try:
            self.client.close()
        finally:
            if self.on_close:
                self.on_close(self)


class Query:

    def __init__(self, host, port, secure=False, loop=None):
        self.connections = set()
        self.host = host
        self.port = port
        self.secure = secure
        self.loop = loop if loop is not None else asyncio.get_event_loop()

    def live(self, cf, callback=None):
        return self._connect_and_send('/live', cf, callback)

    def find(self, cf, callback=None):
        return self._connect_and_send('/find', cf, callback)

    def _connect_and_send(self, path, cf, callback):

        client = Client(loop=self.loop, host=self.host, port=self.port, path=path, recv=callback)

        def _on_close(hnd):
            if hnd in self.connections:
                self.connections.remove(hnd)

        client.connect()

        rh = resultHandler(client, _on_close)
        self.connections.add(rh)

        msg = json.dumps(cf)

        client.send(msg)

        return rh
