clickplc
========

Python ≥3.5 driver and command-line tool for [Koyo Ethernet ClickPLCs](https://www.automationdirect.com/adc/Overview/Catalog/Programmable_Controllers/CLICK_Series_PLCs_(Stackable_Micro_Brick)).

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

This will print all the X, Y, and DF registers to stdout as JSON. You can pipe
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

Currently, only X, Y, and DF are supported. I personally haven't needed to
use the other categories, but they are straightforward to add if needed.
