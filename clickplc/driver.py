"""
A Python driver for Koyo ClickPLC ethernet units.

Distributed under the GNU General Public License v2
Copyright (C) 2020 NuMat Technologies
"""
import csv
import pydoc
from collections import defaultdict
from string import digits
from typing import Union, List

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder

from clickplc.util import AsyncioModbusClient


class ClickPLC(AsyncioModbusClient):
    """Ethernet driver for the Koyo ClickPLC.

    This interface handles the quirks of both Modbus TCP/IP and the ClickPLC,
    abstracting corner cases and providing a simple asynchronous interface.
    """

    data_types = {
        'x': 'bool',    # Input point
        'y': 'bool',    # Output point
        'c': 'bool',    # (C)ontrol relay
        'df': 'float',  # (D)ata register (f)loating point
        'ds': 'int16',  # (D)ata register (s)igned int
        'sd': 'int16',  # (S)ystem (D)ata
    }

    def __init__(self, address, tag_filepath='', timeout=1):
        """Initialize PLC connection and data structure.

        Args:
            address: The PLC IP address or DNS name
            tag_filepath: Path to the PLC tags file
            timeout (optional): Timeout when communicating with PLC. Default 1s.

        """
        super().__init__(address, timeout)
        self.tags = self._load_tags(tag_filepath)
        self.active_addresses = self._get_address_ranges(self.tags)

    def get_tags(self) -> dict:
        """Return all tags and associated configuration information.

        Use this data for debugging or to provide more detailed
        information on user interfaces.

        Returns:
            A dictionary containing information associated with each tag name.

        """
        return self.tags

    async def get(self, address: str = None) -> dict:
        """Get variables from the ClickPLC.

        Args:
            address: ClickPLC address(es) to get. Specify a range with a
                hyphen, e.g. 'DF1-DF40'

        If driver is loaded with a tags file this can be called without an
        address to return all nicknamed addresses in the tags file
        >>> plc.get()
        {'P-101': 0.0, 'P-102': 0.0 ..., T-101:0.0}

        Otherwise one or more internal variable can be requested
        >>> plc.get('df1')
        0.0
        >>> plc.get('df1-df20')
        {'df1': 0.0, 'df2': 0.0, ..., 'df20': 0.0}
        >>> plc.get('y101-y316')
        {'y101': False, 'y102': False, ..., 'y316': False}

        This uses the ClickPLC's internal variable notation, which can be
        found in the Address Picker of the ClickPLC software.
        """
        if address is None:
            if not self.tags:
                raise ValueError('An address must be supplied to get if tags were not '
                                 'provided when driver initialized')
            results = {}
            for category, address in self.active_addresses.items():
                results.update(await getattr(self, '_get_' + category)
                                            (address['min'], address['max']))
            return {tag_name: results[tag_info['id'].lower()]
                    for tag_name, tag_info in self.tags.items()}

        if '-' in address:
            start, end = address.split('-')
        else:
            start, end = address, None
        i = next(i for i, s in enumerate(start) if s.isdigit())
        category, start_index = start[:i].lower(), int(start[i:])
        end_index = None if end is None else int(end[i:])

        if end_index is not None and end_index < start_index:
            raise ValueError("End address must be greater than start address.")
        if category not in self.data_types:
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
        >>> plc.set('myTagNickname', True)  # Sets address named myTagNickname to true

        This uses the ClickPLC's internal variable notation, which can be
        found in the Address Picker of the ClickPLC software. If a tags file
        was loaded at driver initalization, nicknames can be used instead.
        """
        if address in self.tags:
            address = self.tags[address]['id']

        if not isinstance(data, list):
            data = [data]

        i = next(i for i, s in enumerate(address) if s.isdigit())
        category, index = address[:i].lower(), int(address[i:])
        if category not in self.data_types:
            raise ValueError(f"{category} currently unsupported.")
        data_type = self.data_types[category].rstrip(digits)
        for datum in data:
            if type(datum) == int and data_type == 'float':
                datum = float(datum)
            if type(datum) != pydoc.locate(data_type):
                raise ValueError(f"Expected {address} as a {data_type}.")
        return await getattr(self, '_set_' + category)(index, data)

    async def _get_x(self, start: int, end: int) -> dict:
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
                output[f'x{current:03}'] = bit
            elif current % 100 == 32:
                current += 100 - 32
            current += 1
        return output

    async def _get_y(self, start: int, end: int) -> dict:
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
                output[f'y{current:03}'] = bit
            elif current % 100 == 32:
                current += 100 - 32
            current += 1
        return output

    async def _get_c(self, start: int, end: int) -> Union[dict, bool]:
        """Read C addresses. Called by `get`.

        C entries start at 16384 (16385 in the Click software's 1-indexed
        notation). This continues for 2000 bits, ending at 18383.

        The response always returns a full byte of data. If you request
        a number of addresses not divisible by 8, it will have extra data. The
        extra data here is discarded before returning.
        """
        if start < 1 or start > 2000:
            raise ValueError('C start address must be 1-2000.')

        start_coil = 16384 + start - 1
        if end is None:
            count = 1
        else:
            if end <= start or end > 2000:
                raise ValueError('C end address must be >start and <2000.')
            end_coil = 16384 + end - 1
            count = end_coil - start_coil + 1

        coils = await self.read_coils(start_coil, count)
        if count == 1:
            return coils.bits[0]
        return {f'c{(start + i)}': bit for i, bit in enumerate(coils.bits) if i < count}

    async def _get_df(self, start: int, end: int) -> Union[dict, float]:
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

    async def _get_ds(self, start: int, end: int) -> Union[dict, int]:
        """Read DS registers. Called by `get`.

        DS entries start at Modbus address 0 (1 in the Click software's
        1-indexed notation). Each DS entry takes 16 bits.
        """
        if start < 1 or start > 4500:
            raise ValueError('DS must be in [1, 4500]')
        if end is not None and (end < 1 or end > 4500):
            raise ValueError('DS end must be in [1, 4500]')

        address = start - 1
        count = 1 if end is None else (end - start + 1)
        registers = await self.read_registers(address, count)
        decoder = BinaryPayloadDecoder.fromRegisters(registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        if end is None:
            return decoder.decode_16bit_int()
        return {f'ds{n}': decoder.decode_16bit_int() for n in range(start, end + 1)}

    async def _get_sd(self, start: int, end: int) -> Union[dict, int]:
        """Read SD registers. Called by `get`.

        SD entries start at Modbus address 361440 (361441 in the Click software's
        1-indexed notation). Each SD entry takes 16 bits.
        """
        if start < 1 or start > 4500:
            raise ValueError('SD must be in [1, 4500]')
        if end is not None and (end < 1 or end > 4500):
            raise ValueError('SD end must be in [1, 4500]')

        address = 61440 + start - 1
        count = 1 if end is None else (end - start + 1)
        registers = await self.read_registers(address, count)
        decoder = BinaryPayloadDecoder.fromRegisters(registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        if end is None:
            return decoder.decode_16bit_int()
        return {f'sd{n}': decoder.decode_16bit_int() for n in range(start, end + 1)}

    async def _set_x(self, start: int, data: Union[List[bool], bool]):
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

    async def _set_y(self, start: int, data: Union[List[bool], bool]):
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

    async def _set_c(self, start: int, data: Union[List[bool], bool]):
        """Set C addresses. Called by `set`.

        For more information on the quirks of C coils, read the `_get_c`
        docstring.
        """
        if start < 1 or start > 2000:
            raise ValueError('C start address must be 1-2000.')
        coil = 16384 + start - 1

        if isinstance(data, list):
            if len(data) > (2000 - start):
                raise ValueError('Data list longer than available addresses.')
            await self.write_coils(coil, data)
        else:
            await self.write_coil(coil, data)

    async def _set_df(self, start: int, data: Union[List[float], float]):
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

    async def _set_ds(self, start: int, data: Union[List[int], int]):
        """Set DS registers. Called by `set`.

        See _get_ds for more information.
        """
        if start < 1 or start > 4500:
            raise ValueError('DS must be in [1, 4500]')
        address = (start - 1)

        def _pack(value):
            builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                           wordorder=Endian.Little)
            builder.add_16bit_int(int(value))
            return builder.build()

        if isinstance(data, list):
            if len(data) > 4500 - start:
                raise ValueError('Data list longer than available addresses.')
            payload = sum((_pack(d) for d in data), [])
            await self.write_registers(address, payload, skip_encode=True)
        else:
            await self.write_register(address, _pack(data), skip_encode=True)

    def _load_tags(self, tag_filepath: str) -> dict:
        """Load tags from file path.

        This tag file is optional but is needed to identify the appropriate variable names,
        and modbus addresses for tags in use on the PLC.

        """
        if not tag_filepath:
            return {}
        with open(tag_filepath) as csv_file:
            csv_data = csv_file.read().splitlines()
        csv_data[0] = csv_data[0].lstrip('## ')
        parsed = {
            row['Nickname']: {
                'address': {
                    'start': int(row['Modbus Address']),
                },
                'id': row['Address'],
                'comment': row['Address Comment'],
                'type': self.data_types.get(
                    row['Address'].rstrip(digits).lower()
                ),
            }
            for row in csv.DictReader(csv_data)
            if row['Nickname'] and not row['Nickname'].startswith("_")
        }
        for data in parsed.values():
            if not data['comment']:
                del data['comment']
            if not data['type']:
                raise TypeError(
                    f"{data['id']} is an unsupported data type. Open a "
                    "github issue at numat/clickplc to get it added."
                )
        sorted_tags = {k: parsed[k] for k in
                       sorted(parsed, key=lambda k: parsed[k]['address']['start'])}
        return sorted_tags

    @staticmethod
    def _get_address_ranges(tags: dict) -> dict:
        """Determine range of addresses required.

        Parse the loaded tags to determine the range of addresses that must be
        queried to return all values
        """
        address_dict = defaultdict(lambda: {'min': 1, 'max': 1})
        for tag_info in tags.values():
            i = next(i for i, s in enumerate(tag_info['id']) if s.isdigit())
            category, index = tag_info['id'][:i].lower(), int(tag_info['id'][i:])
            address_dict[category]['min'] = min(address_dict[category]['min'], index)
            address_dict[category]['max'] = max(address_dict[category]['max'], index)
        return address_dict
