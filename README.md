clickplc [![Build Status](https://dev.azure.com/numat/NuMat/_apis/build/status/numat.clickplc?branchName=master)](https://dev.azure.com/numat/NuMat/_build/latest?definitionId=3&branchName=master)
========

Python ≥3.6 driver and command-line tool for [Koyo Ethernet ClickPLCs](https://www.automationdirect.com/adc/Overview/Catalog/Programmable_Controllers/CLICK_Series_PLCs_(Stackable_Micro_Brick)).

<p align="center">
  <img src="https://www.automationdirect.com/microsites/clickplcs/images/expandedclick.jpg" />
</p>

Installation
============

```
pip install clickplc
```

Usage
=====

### Command Line

```
$ clickplc the-plc-ip-address
```

This will print all the X, Y, DS, and DF registers to stdout as JSON. You can pipe
this as needed. However, you'll likely want the python functionality below.

### Python

This uses Python ≥3.5's async/await syntax to asynchronously communicate with
a ClickPLC. For example:

```python
import asyncio
from clickplc import ClickPLC

async def get():
    async with ClickPLC('the-plc-ip-address') as plc:
        print(await plc.get('df1-df500'))

asyncio.run(get())
```

The entire API is `get` and `set`, and takes a range of inputs:

```python
>>> await plc.get('df1')
0.0
>>> await plc.get('df1-df20')
{'df1': 0.0, 'df2': 0.0, ..., 'df20': 0.0}
>>> await plc.get('y101-y316')
{'y101': False, 'y102': False, ..., 'y316': False}

>>> await plc.set('df1', 0.0)  # Sets DF1 to 0.0
>>> await plc.set('df1', [0.0, 0.0, 0.0])  # Sets DF1-DF3 to 0.0.
>>> await plc.set('y101', True)  # Sets Y101 to true
```

Currently, only X, Y, C, DS, DF, and CTD are supported:

|  |  |  |
|---|---|---|
| x | bool | Input point |
| y | bool | Output point |
| c | bool | (C)ontrol relay |
| df | float | (D)ata register, (f)loating point |
| ds | int16 | (D)ata register, (s)igned int |
| ctd | int32 | (C)oun(t)er Current Values, (d)ouble int |

We personally haven't needed to use the other categories, but they are
straightforward to add if needed.

### Tags / Nicknames

Recent ClickPLC software provides the ability to export a "tags file", which
contains all variables with user-assigned nicknames. The tags file can be used
with this driver to improve code readability. (Who really wants to think about
modbus addresses and register/coil types?)

To export a tags file, open the ClickPLC software, go to the Address Picker,
select "Display MODBUS address", and export the file.

Once you have this file, simply pass the file path to the driver. You can now
`set` variables by name and `get` all named variables by default.

```python
async with ClickPLC('the-plc-ip-address', 'path-to-tags.csv') as plc:
    await plc.set('my-nickname', True)  # Set variable by nickname
    print(await plc.get())  # Get all named variables in tags file
```

Additionally, the tags file can be used with the commandline tool to provide more informative output:
```
$ clickplc the-plc-ip-address tags-filepath
```
