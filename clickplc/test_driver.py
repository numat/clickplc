import asyncio

from unittest import TestCase

from clickplc.mock import ClickPLC


class TestClickPLC(TestCase):
    """Test the functionality of the ClickPLC driver.

    Tests use the mocked version of the driver which replaces remote communications
    with a local data store
    """

    @classmethod
    def setUp(cls):
        cls.loop = asyncio.get_event_loop()
        cls.clickplc = ClickPLC('fake IP')

    def set(self, *args):
        return self.loop.run_until_complete(self.clickplc.set(*args))

    def get(self, *args):
        return self.loop.run_until_complete(self.clickplc.get(*args))

    def bool_roundtrip(self, prefix):
        self.set(f'{prefix}2', True)
        self.set(f'{prefix}3', [False, True])
        expected = {f'{prefix}001': False, f'{prefix}002': True, f'{prefix}003': False,
                    f'{prefix}004': True, f'{prefix}005': False}
        assert expected == self.get(f'{prefix}1-{prefix}5')

    def test_x_roundtrip(self):
        self.bool_roundtrip('x')

    def test_y_roundtrip(self):
        self.bool_roundtrip('y')

    def test_c_roundtrip(self):
        self.set('c2', True)
        self.set('c3', [False, True])
        expected = {'c1': False, 'c2': True, 'c3': False, 'c4': True, 'c5': False}
        assert expected == self.get('c1-c5')

    def test_df_roundtrip(self):
        self.set('df2', 2.0)
        self.set('df3', [3.0, 4.0])
        expected = {'df1': 0.0, 'df2': 2.0, 'df3': 3.0, 'df4': 4.0, 'df5': 0.0}
        assert expected == self.get('df1-df5')

    def test_ds_roundtrip(self):
        self.set('df2', 2)
        self.set('df3', [3, 4])
        expected = {'df1': 0, 'df2': 2, 'df3': 3, 'df4': 4, 'df5': 0}
        assert expected == self.get('df1-df5')

    def test_get_error_handling(self):
        with self.assertRaisesRegex(ValueError, 'End address must be greater than start address.'):
            self.get('c3-c1')
        with self.assertRaisesRegex(ValueError, 'foo currently unsupported'):
            self.get('foo1')
        with self.assertRaisesRegex(ValueError, 'Inter-category ranges are unsupported.'):
            self.get('c1-x3')

    def test_set_error_handling(self):
        with self.assertRaisesRegex(ValueError, 'foo currently unsupported'):
            self.set('foo1', 1)

    def xy_error_handling(self, prefix):
        with self.assertRaisesRegex(ValueError, 'address must be \\*01-\\*16.'):
            self.get(f'{prefix}17')
        with self.assertRaisesRegex(ValueError, 'address must be in \\[001, 816\\].'):
            self.get(f'{prefix}1001')
        with self.assertRaisesRegex(ValueError, 'address must be \\*01-\\*16.'):
            self.get(f'{prefix}1-{prefix}17')
        with self.assertRaisesRegex(ValueError, 'address must be in \\[001, 816\\].'):
            self.get(f'{prefix}1-{prefix}1001')
        with self.assertRaisesRegex(ValueError, 'address must be \\*01-\\*16.'):
            self.set(f'{prefix}17', True)
        with self.assertRaisesRegex(ValueError, 'address must be in \\[001, 816\\].'):
            self.set(f'{prefix}1001', True)
        with self.assertRaisesRegex(ValueError, 'Data list longer than available addresses.'):
            self.set(f'{prefix}816', [True, True])

    def test_x_error_handling(self):
        self.xy_error_handling("x")

    def test_y_error_handling(self):
        self.xy_error_handling("y")

    def test_c_error_handling(self):
        with self.assertRaisesRegex(ValueError, 'C start address must be 1-2000.'):
            self.get('c2001')
        with self.assertRaisesRegex(ValueError, 'C end address must be >start and <2000.'):
            self.get('c1-c2001')
        with self.assertRaisesRegex(ValueError, 'C start address must be 1-2000.'):
            self.set('c2001', True)
        with self.assertRaisesRegex(ValueError, 'Data list longer than available addresses.'):
            self.set('c2000', [True, True])

    def test_df_error_handling(self):
        with self.assertRaisesRegex(ValueError, 'DF must be in \\[1, 500\\]'):
            self.get('df501')
        with self.assertRaisesRegex(ValueError, 'DF end must be in \\[1, 500\\]'):
            self.get('df1-df501')
        with self.assertRaisesRegex(ValueError, 'DF must be in \\[1, 500\\]'):
            self.set('df501', 1.0)
        with self.assertRaisesRegex(ValueError, 'Data list longer than available addresses.'):
            self.set('df500', [1.0, 2.0])

    def test_ds_error_handling(self):
        with self.assertRaisesRegex(ValueError, 'DS must be in \\[1, 4500\\]'):
            self.get('ds4501')
        with self.assertRaisesRegex(ValueError, 'DS end must be in \\[1, 4500\\]'):
            self.get('ds1-ds4501')
        with self.assertRaisesRegex(ValueError, 'DS must be in \\[1, 4500\\]'):
            self.set('ds4501', 1)
        with self.assertRaisesRegex(ValueError, 'Data list longer than available addresses.'):
            self.set('ds4500', [1, 2])
