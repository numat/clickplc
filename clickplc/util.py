"""Base functionality for modbus communication.

Distributed under the GNU General Public License v2
Copyright (C) 2019 NuMat Technologies
"""
import asyncio

from pymodbus.client.asynchronous.async_io import ReconnectingAsyncioModbusTcpClient
import pymodbus.exceptions


class AsyncioModbusClient(object):
    """A generic asyncio client.

    This expands upon the pymodbus ReconnectionAsyncioModbusTcpClient by
    including standard timeouts, async context manager, and queued requests.
    """

    def __init__(self, address, timeout=1):
        """Set up communication parameters."""
        self.ip = address
        self.timeout = timeout
        self.client = ReconnectingAsyncioModbusTcpClient()
        self.open = False
        self.waiting = False

    async def __aenter__(self):
        """Asynchronously connect with the context manager."""
        await self._connect()
        return self

    async def __aexit__(self, *args):
        """Provide exit to the context manager."""
        self._close()

    async def _connect(self):
        """Start asynchronous reconnect loop."""
        self.waiting = True
        await self.client.start(self.ip)
        self.waiting = False
        if self.client.protocol is None:
            raise IOError("Could not connect to '{}'.".format(self.ip))
        self.open = True

    async def read_coils(self, address, count):
        """Read a modbus coil."""
        return await self._request('read_coils', address, count)

    async def read_registers(self, address, count):
        """Read modbus registers.

        The Modbus protocol doesn't allow responses longer than 250 bytes
        (ie. 125 registers, 62 DF addresses), which this function manages by
        chunking larger requests.
        """
        registers = []
        while count > 124:
            r = await self._request('read_holding_registers', address, 124)
            registers += r.registers
            address, count = address + 124, count - 124
        r = await self._request('read_holding_registers', address, count)
        registers += r.registers
        return registers

    async def write_coil(self, address, value):
        """Write modbus coils."""
        await self._request('write_coil', address, value)

    async def write_coils(self, address, values):
        """Write modbus coils."""
        await self._request('write_coils', address, values)

    async def write_register(self, address, value, skip_encode=False):
        """Write a modbus register."""
        await self._request('write_registers', address, value, skip_encode=skip_encode)

    async def write_registers(self, address, values, skip_encode=False):
        """Write modbus registers.

        The Modbus protocol doesn't allow requests longer than 250 bytes
        (ie. 125 registers, 62 DF addresses), which this function manages by
        chunking larger requests.
        """
        while len(values) > 62:
            await self._request('write_registers',
                                address, values, skip_encode=skip_encode)
            address, values = address + 124, values[62:]
        await self._request('write_registers',
                            address, values, skip_encode=skip_encode)

    async def _request(self, method, *args, **kwargs):
        """Send a request to the device and awaits a response.

        This mainly ensures that requests are sent serially, as the Modbus
        protocol does not allow simultaneous requests (it'll ignore any
        request sent while it's processing something). The driver handles this
        by assuming there is only one client instance. If other clients
        exist, other logic will have to be added to either prevent or manage
        race conditions.
        """
        if not self.open:
            await self._connect()
        while self.waiting:
            await asyncio.sleep(0.1)
        if self.client.protocol is None or not self.client.protocol.connected:
            raise TimeoutError("Not connected to device.")
        try:
            future = getattr(self.client.protocol, method)(*args, **kwargs)
        except AttributeError:
            raise TimeoutError("Not connected to device.")
        self.waiting = True
        try:
            return await asyncio.wait_for(future, timeout=self.timeout)
        except asyncio.TimeoutError as e:
            if self.open:
                # This came from reading through the pymodbus@python3 source
                # Problem was that the driver was not detecting disconnect
                if hasattr(self, 'modbus'):
                    self.client.protocol_lost_connection(self.modbus)
                self.open = False
            raise TimeoutError(e)
        except pymodbus.exceptions.ConnectionException as e:
            raise ConnectionError(e)
        finally:
            self.waiting = False

    def _close(self):
        """Close the TCP connection."""
        self.client.stop()
        self.open = False
        self.waiting = False
