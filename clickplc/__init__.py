"""
A Python driver for Koyo ClickPLC ethernet units.

Distributed under the GNU General Public License v2
Copyright (C) 2019 NuMat Technologies
"""
from clickplc.driver import ClickPLC


def command_line(args=None):
    """Command-line tool for ClickPLC communication."""
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(description="Control a ClickPLC from "
                                     "the command line")
    parser.add_argument('address', help="The IP address of the ClickPLC")
    parser.add_argument('tags_file', nargs="?",
                        help="Optional: Path to a tags file for this PLC")
    args = parser.parse_args(args)

    async def get():
        async with ClickPLC(args.address, args.tags_file) as plc:
            if args.tags_file is not None:
                d = await plc.get()
            else:
                d = await plc.get('x001-x816')
                d.update(await plc.get('y001-y816'))
                d.update(await plc.get('c1-c100'))
                d.update(await plc.get('df1-df100'))
                d.update(await plc.get('ds1-ds100'))
                d.update(await plc.get('ctd1-ctd250'))
            print(json.dumps(d, indent=4))

    loop = asyncio.new_event_loop()
    loop.run_until_complete(get())


if __name__ == '__main__':
    command_line()
