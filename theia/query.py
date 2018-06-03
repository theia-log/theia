import asyncio
from theia.comm import Client
import json
from logging import getLogger


log = getLogger(__name__)


class ResultHandler:

    def __init__(self, client):
        self.client = client
        self._close_handlers = []
        self.client.on_close(self._on_client_closed)
        
    def _on_client_closed(self, websocket, code, reason):
        for hnd in self._close_handlers:
            try:
                hnd(self.client, code, reason)
            except Exception as e:
                log.debug('ResultHandler[%s]: close hander %s error: %s', self.client, hnd, e)
    
    def when_closed(self, closed_handler):
        self._close_handlers.append(closed_handler)
    
    def cancel(self):
        if self.client.is_open():
            self.client.close()


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

        client.connect()
        
        self.connections.add(client)
        
        def on_client_closed(websocket, code, reason):
            # client was closed
            if client in self.connections:
                self.connections.remove(client)
        
        client.on_close(on_client_closed)
        
        msg = json.dumps(cf)

        client.send(msg)
        
        return ResultHandler(client)

