"""Base functionality for modbus communication.

Distributed under the GNU General Public License v2
Copyright (C) 2022 NuMat Technologies
"""
from __future__ import annotations

import asyncio

try:
    from pymodbus.client import AsyncModbusTcpClient  # 3.x
except ImportError:  # 2.4.x - 2.5.x
    from pymodbus.client.asynchronous.async_io import (  # type: ignore
        ReconnectingAsyncioModbusTcpClient,
    )
import pymodbus.exceptions


class AsyncioModbusClient:
    """A generic asyncio client.

    This expands upon the pymodbus AsyncModbusTcpClient by
    including standard timeouts, async context manager, and queued requests.
    """

    def __init__(self, address, timeout=1):
        """Set up communication parameters."""
        self.ip = address
        self.timeout = timeout
        self._detect_pymodbus_version()
        if self.pymodbus30plus:
            self.client = AsyncModbusTcpClient(address, timeout=timeout)
        else:  # 2.x
            self.client = ReconnectingAsyncioModbusTcpClient()
        self.lock = asyncio.Lock()
        self.connectTask = asyncio.create_task(self._connect())

    async def __aenter__(self):
        """Asynchronously connect with the context manager."""
        return self

    async def __aexit__(self, *args) -> None:
        """Provide exit to the context manager."""
        await self._close()

    def _detect_pymodbus_version(self) -> None:
        """Detect various pymodbus versions."""
        self.pymodbus30plus = int(pymodbus.__version__[0]) == 3
        self.pymodbus32plus = self.pymodbus30plus and int(pymodbus.__version__[2]) >= 2
        self.pymodbus33plus = self.pymodbus30plus and int(pymodbus.__version__[2]) >= 3
        self.pymodbus35plus = self.pymodbus30plus and int(pymodbus.__version__[2]) >= 5

    async def _connect(self) -> None:
        """Start asynchronous reconnect loop."""
        try:
            if self.pymodbus30plus:
                await asyncio.wait_for(self.client.connect(), timeout=self.timeout)  # 3.x
            else:  # 2.4.x - 2.5.x
                await self.client.start(self.ip)  # type: ignore
        except Exception:
            raise OSError(f"Could not connect to '{self.ip}'.")

    async def read_coils(self, address: int, count):
        """Read modbus output coils (0 address prefix)."""
        return await self._request('read_coils', address, count)

    async def read_registers(self, address: int, count):
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

    async def write_coil(self, address: int, value):
        """Write modbus coils."""
        await self._request('write_coil', address, value)

    async def write_coils(self, address: int, values):
        """Write modbus coils."""
        await self._request('write_coils', address, values)

    async def write_register(self, address: int, value, skip_encode=False):
        """Write a modbus register."""
        await self._request('write_register', address, value, skip_encode=skip_encode)

    async def write_registers(self, address: int, values, skip_encode=False):
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
        await self.connectTask
        async with self.lock:
            try:
                if self.pymodbus32plus:
                    future = getattr(self.client, method)
                else:
                    future = getattr(self.client.protocol, method)  # type: ignore
                return await future(*args, **kwargs)
            except (asyncio.TimeoutError, pymodbus.exceptions.ConnectionException):
                raise TimeoutError("Not connected to PLC.")

    async def _close(self):
        """Close the TCP connection."""
        if self.pymodbus33plus:
            self.client.close()  # 3.3.x
        elif self.pymodbus30plus:
            await self.client.close()  # type: ignore  # 3.0.x - 3.2.x
        else:  # 2.4.x - 2.5.x
            self.client.stop()  # type: ignore
