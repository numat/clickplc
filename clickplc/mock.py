"""
Python mock driver for AutomationDirect (formerly Koyo) ClickPLCs.

Uses local storage instead of remote communications.

Distributed under the GNU General Public License v2
Copyright (C) 2021 NuMat Technologies
"""
from collections import defaultdict
from unittest.mock import MagicMock

from pymodbus.bit_read_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.bit_write_message import WriteSingleCoilResponse, WriteMultipleCoilsResponse
from pymodbus.register_read_message import ReadHoldingRegistersResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse

from clickplc.driver import ClickPLC as realClickPLC


class AsyncMock(MagicMock):
    """Magic mock that works with async methods."""

    async def __call__(self, *args, **kwargs):
        """Convert regular mocks into into an async coroutine."""
        return super(AsyncMock, self).__call__(*args, **kwargs)


class ClickPLC(realClickPLC):
    """A version of the driver replacing remote communication with local storage for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = AsyncMock()
        self._coils = defaultdict(bool)
        self._discrete_inputs = defaultdict(bool)
        self._registers = defaultdict(bytes)

    async def _request(self, method, *args, **kwargs):
        if method == 'read_coils':
            address, count = args
            return ReadCoilsResponse([self._coils[address + i] for i in range(count)])
        if method == 'read_discrete_inputs':
            address, count = args
            return ReadDiscreteInputsResponse([self._discrete_inputs[address + i]
                                               for i in range(count)])
        elif method == 'read_holding_registers':
            address, count = args
            return ReadHoldingRegistersResponse([int.from_bytes(self._registers[address + i],
                                                                byteorder='big')
                                                 for i in range(count)])
        elif method == 'write_coil':
            address, data = args
            self._coils[address] = data
            return WriteSingleCoilResponse(address, data)
        elif method == 'write_coils':
            address, data = args
            for i, d in enumerate(data):
                self._coils[address + i] = d
            return WriteMultipleCoilsResponse(address, data)
        elif method == 'write_registers':
            address, data = args
            for i, d in enumerate(data):
                self._registers[address + i] = d
            return WriteMultipleRegistersResponse(address, data)
        return NotImplementedError(f'Unrecognised method: {method}')
