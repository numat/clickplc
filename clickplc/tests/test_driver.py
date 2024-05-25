"""Test the driver correctly parses a tags file and responds with correct data."""
from unittest import mock

import pytest

from clickplc import command_line
from clickplc.mock import ClickPLC

ADDRESS = 'fakeip'
# from clickplc.driver import ClickPLC
# ADDRESS = '172.16.0.168'


@pytest.fixture(scope='session')
async def plc_driver():
    """Confirm the driver correctly initializes without a tags file."""
    async with ClickPLC(ADDRESS) as c:
        yield c

@pytest.fixture
def expected_tags():
    """Return the tags defined in the tags file."""
    return {
        'IO2_24V_OK': {'address': {'start': 16397}, 'id': 'C13', 'type': 'bool'},
        'IO2_Module_OK': {'address': {'start': 16396}, 'id': 'C12', 'type': 'bool'},
        'LI_101': {'address': {'start': 428683}, 'id': 'DF6', 'type': 'float'},
        'LI_102': {'address': {'start': 428681}, 'id': 'DF5', 'type': 'float'},
        'P_101': {'address': {'start': 8289}, 'id': 'Y301', 'type': 'bool'},
        'P_101_auto': {'address': {'start': 16385}, 'id': 'C1', 'type': 'bool'},
        'P_102_auto': {'address': {'start': 16386}, 'id': 'C2', 'type': 'bool'},
        'P_103': {'address': {'start': 8290}, 'id': 'Y302', 'type': 'bool'},
        'TIC101_PID_ErrorCode': {'address': {'start': 400100},
                                 'comment': 'PID Error Code',
                                 'id': 'DS100',
                                 'type': 'int16'},
        'TI_101': {'address': {'start': 428673}, 'id': 'DF1', 'type': 'float'},
        'VAHH_101_OK': {'address': {'start': 16395}, 'id': 'C11', 'type': 'bool'},
        'VAH_101_OK': {'address': {'start': 16394}, 'id': 'C10', 'type': 'bool'},
        'VI_101': {'address': {'start': 428685}, 'id': 'DF7', 'type': 'float'},
        'PLC_Error_Code': {'address': {'start': 361441}, 'id': 'SD1', 'type': 'int16'},
        'timer': {'address': {'start': 449153}, 'id': 'CTD1', 'type': 'int32'},
    }


@mock.patch('clickplc.ClickPLC', ClickPLC)
def test_driver_cli(capsys):
    """Confirm the commandline interface works without a tags file."""
    command_line([ADDRESS])
    captured = capsys.readouterr()
    assert 'x816' in captured.out
    assert 'c100' in captured.out
    assert 'df100' in captured.out


@mock.patch('clickplc.ClickPLC', ClickPLC)
def test_driver_cli_tags(capsys):
    """Confirm the commandline interface works with a tags file."""
    command_line([ADDRESS, 'clickplc/tests/plc_tags.csv'])
    captured = capsys.readouterr()
    assert 'P_101' in captured.out
    assert 'VAHH_101_OK' in captured.out
    assert 'TI_101' in captured.out
    with pytest.raises(SystemExit):
        command_line([ADDRESS, 'tags', 'bogus'])


@pytest.mark.asyncio(scope='session')
async def test_unsupported_tags():
    """Confirm the driver detects an improper tags file."""
    with pytest.raises(TypeError, match='unsupported data type'):
        ClickPLC(ADDRESS, 'clickplc/tests/bad_tags.csv')


@pytest.mark.asyncio(scope='session')
async def test_tagged_driver(expected_tags):
    """Test a roundtrip with the driver using a tags file."""
    async with ClickPLC(ADDRESS, 'clickplc/tests/plc_tags.csv') as tagged_driver:
        await tagged_driver.set('VAH_101_OK', True)
        state = await tagged_driver.get()
        assert state.get('VAH_101_OK')
        assert expected_tags == tagged_driver.get_tags()


@pytest.mark.asyncio(scope='session')
async def test_y_roundtrip(plc_driver):
    """Confirm y (output bools) are read back correctly after being set."""
    await plc_driver.set('y1', [False, True, False, True])
    expected = {'y001': False, 'y002': True, 'y003': False, 'y004': True}
    assert expected == await plc_driver.get('y1-y4')
    await plc_driver.set('y816', True)
    assert await plc_driver.get('y816') is True


@pytest.mark.asyncio(scope='session')
async def test_c_roundtrip(plc_driver):
    """Confirm c bools are read back correctly after being set."""
    await plc_driver.set('c2', True)
    await plc_driver.set('c3', [False, True])
    expected = {'c1': False, 'c2': True, 'c3': False, 'c4': True, 'c5': False}
    assert expected == await plc_driver.get('c1-c5')
    await plc_driver.set('c2000', True)
    assert await plc_driver.get('c2000') is True


@pytest.mark.asyncio(scope='session')
async def test_df_roundtrip(plc_driver):
    """Confirm df floats are read back correctly after being set."""
    await plc_driver.set('df1', 0.0)
    await plc_driver.set('df2', [2.0, 3.0, 4.0, 0.0])
    expected = {'df1': 0.0, 'df2': 2.0, 'df3': 3.0, 'df4': 4.0, 'df5': 0.0}
    assert expected == await plc_driver.get('df1-df5')
    await plc_driver.set('df500', 1.0)
    assert await plc_driver.get('df500') == 1.0


@pytest.mark.asyncio(scope='session')
async def test_ds_roundtrip(plc_driver):
    """Confirm ds ints are read back correctly after being set."""
    await plc_driver.set('ds2', 2)
    await plc_driver.set('ds3', [-32768, 32767])
    expected = {'ds1': 0, 'ds2': 2, 'ds3': -32768, 'ds4': 32767, 'ds5': 0}
    assert expected == await plc_driver.get('ds1-ds5')
    await plc_driver.set('ds4500', 4500)
    assert await plc_driver.get('ds4500') == 4500


@pytest.mark.asyncio(scope='session')
async def test_get_error_handling(plc_driver):
    """Confirm the driver gives an error on invalid get() calls."""
    with pytest.raises(ValueError, match='An address must be supplied'):
        await plc_driver.get()
    with pytest.raises(ValueError, match='End address must be greater than start address'):
        await plc_driver.get('c3-c1')
    with pytest.raises(ValueError, match='foo currently unsupported'):
        await plc_driver.get('foo1')
    with pytest.raises(ValueError, match='Inter-category ranges are unsupported'):
        await plc_driver.get('c1-x3')


@pytest.mark.asyncio(scope='session')
async def test_set_error_handling(plc_driver):
    """Confirm the driver gives an error on invalid set() calls."""
    with pytest.raises(ValueError, match='foo currently unsupported'):
        await plc_driver.set('foo1', 1)


@pytest.mark.asyncio(scope='session')
@pytest.mark.parametrize('prefix', ['x', 'y'])
async def test_get_xy_error_handling(plc_driver, prefix):
    """Ensure errors are handled for invalid get requests of x and y registers."""
    with pytest.raises(ValueError, match=r'address must be \*01-\*16.'):
        await plc_driver.get(f'{prefix}17')
    with pytest.raises(ValueError, match=r'address must be in \[001, 816\].'):
        await plc_driver.get(f'{prefix}1001')
    with pytest.raises(ValueError, match=r'address must be \*01-\*16.'):
        await plc_driver.get(f'{prefix}1-{prefix}17')
    with pytest.raises(ValueError, match=r'address must be in \[001, 816\].'):
        await plc_driver.get(f'{prefix}1-{prefix}1001')


@pytest.mark.asyncio(scope='session')
async def test_set_y_error_handling(plc_driver):
    """Ensure errors are handled for invalid set requests of y registers."""
    with pytest.raises(ValueError, match=r'address must be \*01-\*16.'):
        await plc_driver.set('y17', True)
    with pytest.raises(ValueError, match=r'address must be in \[001, 816\].'):
        await plc_driver.set('y1001', True)
    with pytest.raises(ValueError, match=r'Data list longer than available addresses.'):
        await plc_driver.set('y816', [True, True])


@pytest.mark.asyncio(scope='session')
async def test_c_error_handling(plc_driver):
    """Ensure errors are handled for invalid requests of c registers."""
    with pytest.raises(ValueError, match=r'C start address must be 1-2000.'):
        await plc_driver.get('c2001')
    with pytest.raises(ValueError, match=r'C end address must be >start and <2000.'):
        await plc_driver.get('c1-c2001')
    with pytest.raises(ValueError, match=r'C start address must be 1-2000.'):
        await plc_driver.set('c2001', True)
    with pytest.raises(ValueError, match=r'Data list longer than available addresses.'):
        await plc_driver.set('c2000', [True, True])


@pytest.mark.asyncio(scope='session')
async def test_df_error_handling(plc_driver):
    """Ensure errors are handled for invalid requests of df registers."""
    with pytest.raises(ValueError, match=r'DF must be in \[1, 500\]'):
        await plc_driver.get('df501')
    with pytest.raises(ValueError, match=r'DF end must be in \[1, 500\]'):
        await plc_driver.get('df1-df501')
    with pytest.raises(ValueError, match=r'DF must be in \[1, 500\]'):
        await plc_driver.set('df501', 1.0)
    with pytest.raises(ValueError, match=r'Data list longer than available addresses.'):
        await plc_driver.set('df500', [1.0, 2.0])


@pytest.mark.asyncio(scope='session')
async def test_ds_error_handling(plc_driver):
    """Ensure errors are handled for invalid requests of ds registers."""
    with pytest.raises(ValueError, match=r'DS must be in \[1, 4500\]'):
        await plc_driver.get('ds4501')
    with pytest.raises(ValueError, match=r'DS end must be in \[1, 4500\]'):
        await plc_driver.get('ds1-ds4501')
    with pytest.raises(ValueError, match=r'DS must be in \[1, 4500\]'):
        await plc_driver.set('ds4501', 1)
    with pytest.raises(ValueError, match=r'Data list longer than available addresses.'):
        await plc_driver.set('ds4500', [1, 2])


@pytest.mark.asyncio(scope='session')
async def test_ctd_error_handling(plc_driver):
    """Ensure errors are handled for invalid requests of ctd registers."""
    with pytest.raises(ValueError, match=r'CTD must be in \[1, 250\]'):
        await plc_driver.get('ctd251')
    with pytest.raises(ValueError, match=r'CTD end must be in \[1, 250\]'):
        await plc_driver.get('ctd1-ctd251')


@pytest.mark.asyncio(scope='session')
@pytest.mark.parametrize('prefix', ['x', 'y', 'c'])
async def test_bool_typechecking(plc_driver, prefix):
    """Ensure errors are handled for set() requests that should be bools."""
    with pytest.raises(ValueError, match='Expected .+ as a bool'):
        await plc_driver.set(f'{prefix}1', 1)
    with pytest.raises(ValueError, match='Expected .+ as a bool'):
        await plc_driver.set(f'{prefix}1', [1.0, 1])


@pytest.mark.asyncio(scope='session')
async def test_df_typechecking(plc_driver):
    """Ensure errors are handled for set() requests that should be floats."""
    await plc_driver.set('df1', 1)
    with pytest.raises(ValueError, match='Expected .+ as a float'):
        await plc_driver.set('df1', True)
    with pytest.raises(ValueError, match='Expected .+ as a float'):
        await plc_driver.set('df1', [True, True])


@pytest.mark.asyncio(scope='session')
async def test_ds_typechecking(plc_driver):
    """Ensure errors are handled for set() requests that should be ints."""
    with pytest.raises(ValueError, match='Expected .+ as a int'):
        await plc_driver.set('ds1', 1.0)
    with pytest.raises(ValueError, match='Expected .+ as a int'):
        await plc_driver.set('ds1', True)
    with pytest.raises(ValueError, match='Expected .+ as a int'):
        await plc_driver.set('ds1', [True, True])
