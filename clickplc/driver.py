"""
A Python driver for Koyo ClickPLC ethernet units.

Distributed under the GNU General Public License v2
Copyright (C) 2019 NuMat Technologies
"""
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder

from clickplc.util import AsyncioModbusClient


class ClickPLC(AsyncioModbusClient):
    """Ethernet driver for the Koyo ClickPLC.

    This interface handles the quirks of both Modbus TCP/IP and the ClickPLC,
    abstracting corner cases and providing a simple asynchronous interface.
    """

    supported = ['x', 'y', 'df']

    async def get(self, address):
        """Get variables from the ClickPLC.

        Args:
            address: ClickPLC address(es) to get. Specify a range with a
                hyphen, e.g. 'DF1-DF40'
            data: A value or list of values to set.

        >>> plc.get('df1')
        0.0
        >>> plc.get('df1-df20')
        {'df1': 0.0, 'df2': 0.0, ..., 'df20': 0.0}
        >>> plc.get('y101-y316')
        {'y101': False, 'y102': False, ..., 'y316': False}

        This uses the ClickPLC's internal variable notation, which can be
        found in the Address Picker of the ClickPLC software.
        """
        if '-' in address:
            start, end = address.split('-')
        else:
            start, end = address, None
        i = start.index(next(s for s in start if s.isdigit()))
        category, start_index = start[:i].lower(), int(start[i:])
        end_index = None if end is None else int(end[i:])

        if end_index is not None and end_index < start_index:
            raise ValueError("End address must be greater than start address.")
        if category not in self.supported:
            raise ValueError("{} currently unsupported.".format(category))
        if end is not None and end[:i].lower() != category:
            raise ValueError("Inter-category ranges are unsupported.")
        return await getattr(self, '_get_' + category)(start_index, end_index)

    async def set(self, address, data):
        """Set values on the ClickPLC.

        Args:
            address: ClickPLC address to set. If `data` is a list, it will set
                this and subsequent addresses.
            data: A value or list of values to set.

        >>> plc.set('df1', 0.0)  # Sets DF1 to 0.0
        >>> plc.set('df1', [0.0, 0.0, 0.0])  # Sets DF1-DF3 to 0.0.
        >>> plc.set('y101', True)  # Sets Y101 to true

        This uses the ClickPLC's internal variable notation, which can be
        found in the Address Picker of the ClickPLC software.
        """
        if not isinstance(data, list):
            data = [data]

        i = address.index(next(s for s in address if s.isdigit()))
        category, index = address[:i].lower(), int(address[i:])
        if category not in self.supported:
            raise ValueError("{} currently unsupported.".format(category))
        return await getattr(self, '_set_' + category)(index, data)

    async def _get_x(self, start, end):
        """Read X addresses. Called by `get`.

        X entries start at 0 (1 in the Click software's 1-indexed
        notation). This function also handles some of the quirks of the unit.

        First, the modbus addresses aren't sequential. Instead, the pattern is:
            X001 0
            [...]
            X016 15
            X101 32
            [...]
        The X addressing only goes up to *16, then jumps 16 coils to get to
        the next hundred. Rather than the overhead of multiple requests, this
        is handled by reading all the data and throwing away unowned addresses.

        Second, the response always returns a full byte of data. If you request
        a number of addresses not divisible by 8, it will have extra data. The
        extra data here is discarded before returning.
        """
        if start % 100 == 0 or start % 100 > 16:
            raise ValueError('X start address must be *01-*16.')
        if start < 1 or start > 816:
            raise ValueError('X start address must be in [001, 816].')

        start_coil = 32 * (start // 100) + start % 100 - 1
        if end is None:
            count = 1
        else:
            if end % 100 == 0 or end % 100 > 16:
                raise ValueError('X end address must be *01-*16.')
            if end < 1 or end > 816:
                raise ValueError('X end address must be in [001, 816].')
            end_coil = 32 * (end // 100) + end % 100 - 1
            count = end_coil - start_coil + 1

        coils = await self.read_coils(start_coil, count)
        if count == 1:
            return coils.bits[0]
        output = {}
        current = start
        for bit in coils.bits:
            if current > end:
                break
            elif current % 100 <= 16:
                output['x{:03d}'.format(current)] = bit
            elif current % 100 == 32:
                current += 100 - 32
            current += 1
        return output

    async def _get_y(self, start, end):
        """Read Y addresses. Called by `get`.

        Y entries start at 8192 (8193 in the Click software's 1-indexed
        notation). This function also handles some of the quirks of the unit.

        First, the modbus addresses aren't sequential. Instead, the pattern is:
            Y001 8192
            [...]
            Y016 8208
            Y101 8224
            [...]
        The Y addressing only goes up to *16, then jumps 16 coils to get to
        the next hundred. Rather than the overhead of multiple requests, this
        is handled by reading all the data and throwing away unowned addresses.

        Second, the response always returns a full byte of data. If you request
        a number of addresses not divisible by 8, it will have extra data. The
        extra data here is discarded before returning.
        """
        if start % 100 == 0 or start % 100 > 16:
            raise ValueError('Y start address must be *01-*16.')
        if start < 1 or start > 816:
            raise ValueError('Y start address must be in [001, 816].')

        start_coil = 8192 + 32 * (start // 100) + start % 100 - 1
        if end is None:
            count = 1
        else:
            if end % 100 == 0 or end % 100 > 16:
                raise ValueError('Y end address must be *01-*16.')
            if end < 1 or end > 816:
                raise ValueError('Y end address must be in [001, 816].')
            end_coil = 8192 + 32 * (end // 100) + end % 100 - 1
            count = end_coil - start_coil + 1

        coils = await self.read_coils(start_coil, count)
        if count == 1:
            return coils.bits[0]
        output = {}
        current = start
        for bit in coils.bits:
            if current > end:
                break
            elif current % 100 <= 16:
                output['y{:03d}'.format(current)] = bit
            elif current % 100 == 32:
                current += 100 - 32
            current += 1
        return output

    async def _get_df(self, start, end):
        """Read DF registers. Called by `get`.

        DF entries start at Modbus address 28672 (28673 in the Click software's
        1-indexed notation). Each DF entry takes 32 bits, or 2 16-bit
        registers.
        """
        if start < 1 or start > 500:
            raise ValueError('DF must be in [1, 500]')
        if end is not None and (end < 1 or end > 500):
            raise ValueError('DF end must be in [1, 500]')

        address = 28672 + 2 * (start - 1)
        count = 2 * (1 if end is None else (end - start + 1))
        registers = await self.read_registers(address, count)
        decoder = BinaryPayloadDecoder.fromRegisters(registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        if end is None:
            return decoder.decode_32bit_float()
        return {f'df{n}': decoder.decode_32bit_float() for n in range(start, end + 1)}

    async def _set_x(self, start, data):
        """Set X addresses. Called by `set`.

        For more information on the quirks of X coils, read the `_get_x`
        docstring.
        """
        if start % 100 == 0 or start % 100 > 16:
            raise ValueError('X start address must be *01-*16.')
        if start < 1 or start > 816:
            raise ValueError('X start address must be in [001, 816].')
        coil = 32 * (start // 100) + start % 100 - 1

        if isinstance(data, list):
            if len(data) > 16 * (9 - start // 100) - start % 100:
                raise ValueError('Data list longer than available addresses.')
            payload = []
            if (start % 100) + len(data) > 16:
                i = 17 - (start % 100)
                payload += data[:i] + [False] * 16
                data = data[i:]
            while len(data) > 16:
                payload += data[:16] + [False] * 16
                data = data[16:]
            payload += data
            await self.write_coils(coil, payload)
        else:
            await self.write_coil(coil, data)

    async def _set_y(self, start, data):
        """Set Y addresses. Called by `set`.

        For more information on the quirks of Y coils, read the `_get_y`
        docstring.
        """
        if start % 100 == 0 or start % 100 > 16:
            raise ValueError('Y start address must be *01-*16.')
        if start < 1 or start > 816:
            raise ValueError('Y start address must be in [001, 816].')
        coil = 8192 + 32 * (start // 100) + start % 100 - 1

        if isinstance(data, list):
            if len(data) > 16 * (9 - start // 100) - start % 100:
                raise ValueError('Data list longer than available addresses.')
            payload = []
            if (start % 100) + len(data) > 16:
                i = 17 - (start % 100)
                payload += data[:i] + [False] * 16
                data = data[i:]
            while len(data) > 16:
                payload += data[:16] + [False] * 16
                data = data[16:]
            payload += data
            await self.write_coils(coil, payload)
        else:
            await self.write_coil(coil, data)

    async def _set_df(self, start, data):
        """Set DF registers. Called by `set`.

        The ClickPLC is little endian, but on registers ("words") instead
        of bytes. As an example, take a random floating point number:
            Input: 0.1
            Hex: 3dcc cccd (IEEE-754 float32)
            Click: -1.076056E8
            Hex: cccd 3dcc
        To fix, we need to flip the registers. Implemented below in `pack`.
        """
        if start < 1 or start > 500:
            raise ValueError('DF must be in [1, 500]')
        address = 28672 + 2 * (start - 1)

        def _pack(value):
            builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                           wordorder=Endian.Little)
            builder.add_32bit_float(float(value))
            return builder.build()

        if isinstance(data, list):
            if len(data) > 500 - start:
                raise ValueError('Data list longer than available addresses.')
            payload = sum((_pack(d) for d in data), [])
            await self.write_registers(address, payload, skip_encode=True)
        else:
            await self.write_register(address, _pack(data), skip_encode=True)
