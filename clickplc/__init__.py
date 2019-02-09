#!/usr/bin/python
"""
A Python driver for Koyo ClickPLC ethernet units.

Distributed under the GNU General Public License v2
Copyright (C) 2019 NuMat Technologies
"""
from clickplc.driver import ClickPLC


def command_line():
    """Command-line tool for ClickPLC communication."""
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(description="Control a ClickPLC from "
                                     "the command line.")
    parser.add_argument('address', help="The IP address of the ClickPLC.")
    args = parser.parse_args()

    async def get():
        async with ClickPLC(args.address) as plc:
            d = await plc.get('x001-x816')
            d.update(await plc.get('y001-y816'))
            d.update(await plc.get('df1-df500'))
            print(json.dumps(d, indent=4))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(get())
    loop.close()


if __name__ == '__main__':
    command_line()
