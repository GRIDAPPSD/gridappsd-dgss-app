# -*- coding: utf-8 -*-
"""
asyncio-server.py
~~~~~~~~~~~~~~~~~

A fully-functional HTTP/2 server using asyncio. Requires Python 3.5+.

This example demonstrates handling requests with bodies, as well as handling
those without. In particular, it demonstrates the fact that DataReceived may
be called multiple times, and that applications must handle that possibility.
"""
import asyncio
import io
import json
import ssl
import collections
from typing import List, Tuple

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import (
    ConnectionTerminated, DataReceived, RemoteSettingsChanged,
    RequestReceived, StreamEnded, StreamReset, WindowUpdated
)
from h2.errors import ErrorCodes
from h2.exceptions import ProtocolError, StreamClosedError
from h2.settings import SettingCodes

from gridappsd import GridAPPSD, topics
from gridappsd.simulation import Simulation, SimulationConfig, PowerSystemConfig


RequestData = collections.namedtuple('RequestData', ['headers', 'data'])
simulation_id = None
sim = None

class H2Protocol(asyncio.Protocol):
    def __init__(self):
        config = H2Configuration(client_side=False, header_encoding='utf-8')
        self.conn = H2Connection(config=config)
        self.transport = None
        self.stream_data = {}
        self.flow_control_futures = {}

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport
        self.conn.initiate_connection()
        self.transport.write(self.conn.data_to_send())

    def connection_lost(self, exc):
        for future in self.flow_control_futures.values():
            future.cancel()
        self.flow_control_futures = {}

    def data_received(self, data: bytes):
        try:
            events = self.conn.receive_data(data)
        except ProtocolError as e:
            self.transport.write(self.conn.data_to_send())
            self.transport.close()
        else:
            self.transport.write(self.conn.data_to_send())
            for event in events:
                print('************************')
                print(event)
                print('************************')
                if isinstance(event, RequestReceived):
                    self.request_received(event.headers, event.stream_id)
                elif isinstance(event, DataReceived):
                    self.receive_data(event.data, event.stream_id)
                elif isinstance(event, StreamEnded):
                    self.stream_complete(event.stream_id)
                elif isinstance(event, ConnectionTerminated):
                    self.transport.close()
                elif isinstance(event, StreamReset):
                    self.stream_reset(event.stream_id)
                elif isinstance(event, WindowUpdated):
                    self.window_updated(event.stream_id, event.delta)
                elif isinstance(event, RemoteSettingsChanged):
                    if SettingCodes.INITIAL_WINDOW_SIZE in event.changed_settings:
                        self.window_updated(None, 0)

                self.transport.write(self.conn.data_to_send())

    def request_received(self, headers: List[Tuple[str, str]], stream_id: int):
        headers = collections.OrderedDict(headers)
        method = headers[':method']

        # Store off the request data.
        request_data = RequestData(headers, io.BytesIO())
        self.stream_data[stream_id] = request_data

    def stream_complete(self, stream_id: int):
        """
        When a stream is complete, we can send our response.
        """
        try:
            request_data = self.stream_data[stream_id]
        except KeyError:
            # Just return, we probably 405'd this already
            return

        headers = request_data.headers
        self.stream_id = stream_id

        response_headers = (
            (':status', '200'),
            ('content-type', 'application/json'),
            ('server', 'asyncio-h2'),
        )
        self.conn.send_headers(self.stream_id, response_headers)
        asyncio.ensure_future(self.send_data(self.stream_id))

               

    def receive_data(self, data: bytes, stream_id: int):
        """
        We've received some data on a stream. If that stream is one we're
        expecting data on, save it off. Otherwise, reset the stream.
        """
        try:
            stream_data = self.stream_data[stream_id]
        except KeyError:
            self.conn.reset_stream(
                stream_id, error_code=ErrorCodes.PROTOCOL_ERROR
            )
        else:
            stream_data.data.write(data)

    def stream_reset(self, stream_id):
        """
        A stream reset was sent. Stop sending data.
        """
        if stream_id in self.flow_control_futures:
            future = self.flow_control_futures.pop(stream_id)
            future.cancel()


    def on_simulation_output(self, header, message):

        message = json.dumps(message, indent=2).encode('utf-8')

        chunk_size = min(
            self.conn.local_flow_control_window(self.stream_id),
            len(message),
            self.conn.max_outbound_frame_size,
        )

        try:
            self.conn.send_data(
                self.stream_id,
                message[:chunk_size],
                end_stream=False
            )
        except (StreamClosedError, ProtocolError):
            # The stream got closed and we didn't get told. We're done
            # here.
            print('Stream got closed')

        self.transport.write(self.conn.data_to_send())
        
        #self.send_data(data, self.stream_id, False)
        #asyncio.ensure_future(self.send_data(data, self.stream_id, True))



    async def send_data(self, stream_id):
        """
        Send data according to the flow control rules.
        """
        while self.conn.local_flow_control_window(stream_id) < 1:
            try:
                await self.wait_for_flow_control(stream_id)
            except asyncio.CancelledError:
                return

        print(simulation_id)
        gapps.subscribe(topics.simulation_output_topic(simulation_id), self.on_simulation_output)

        
        

    async def wait_for_flow_control(self, stream_id):
        """
        Waits for a Future that fires when the flow control window is opened.
        """
        f = asyncio.Future()
        self.flow_control_futures[stream_id] = f
        await f

    def window_updated(self, stream_id, delta):
        """
        A window update frame was received. Unblock some number of flow control
        Futures.
        """
        if stream_id and stream_id in self.flow_control_futures:
            f = self.flow_control_futures.pop(stream_id)
            f.set_result(delta)
        elif not stream_id:
            for f in self.flow_control_futures.values():
                f.set_result(delta)

            self.flow_control_futures = {}


def run_simulation(gapps: GridAPPSD):
    feeder_mrid = "_A3BC35AA-01F6-478E-A7B1-8EA4598A685C"
    psc = PowerSystemConfig(Line_name=feeder_mrid)
    sim_conf = SimulationConfig(power_system_config = psc)
    sim_config = json.loads(json.dumps(sim_conf.asdict(), indent = 2))
    global sim
    sim = Simulation(gapps, run_config=sim_config)
    sim.start_simulation()
    print(f"Started Simulation with id {sim.simulation_id}")
    return sim.simulation_id
    
gapps = GridAPPSD()
simulation_id = run_simulation(gapps)

loop = asyncio.get_event_loop()
# Each client connection will create a new protocol instance
coro = loop.create_server(H2Protocol, '127.0.0.1', 8443)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    sim.stop()
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()