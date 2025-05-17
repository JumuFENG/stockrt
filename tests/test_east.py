import unittest
from stockrt import rtsource

class TestEmFunctions(unittest.TestCase):
    source = rtsource('em')
    def test_single_stock_quotes(self):
        stock_code = '000001'
        result = self.source.quotes(stock_code)
        self.assertIsInstance(result, dict)
        stock_data = result.get('000001')
        self.assertIsNotNone(stock_data)
        self.assertIsInstance(stock_data, dict)
        required_keys = ['name', 'price', 'change', 'high', 'low', 'open', 'lclose', 'volume', 'amount']
        for key in required_keys:
            self.assertIn(key, stock_data)
            self.assertIsNotNone(stock_data[key])

    def test_list_of_stock_codes_quotes(self):
        stock_codes = ['000001', '000002']
        result = self.source.quotes(stock_codes)
        self.assertIsInstance(result, dict)

    def test_single_stock_quotes5(self):
        stock_codes = '000001'
        result = self.source.quotes5(stock_codes)
        self.assertIsInstance(result, dict)

    def test_list_of_stock_codes_quotes5(self):
        stock_codes = ['000001', 'sh000001']
        result = self.source.quotes5(stock_codes)
        self.assertIsInstance(result, dict)

    def test_single_stock_tlines(self):
        stock_codes = '000001'
        result = self.source.quotes(stock_codes)
        self.assertIsInstance(result, dict)

    def test_list_of_stock_codes_tlines(self):
        stock_codes = ['000001', 'sh000001']
        result = self.source.quotes(stock_codes)
        self.assertIsInstance(result, dict)

    def test_single_stock_mklines(self):
        stock_codes = '000001'
        result = self.source.mklines(stock_codes, 1, 10)
        self.assertIsInstance(result, dict)

    def test_list_of_stock_codes_mklines(self):
        stock_codes = ['000001', 'sh000001']
        result = self.source.mklines(stock_codes, 5, 10)
        self.assertIsInstance(result, dict)

    def test_single_stock_dklines(self):
        stock_codes = '000001'
        result = self.source.dklines(stock_codes, 'd', 10)
        self.assertIsInstance(result, dict)

    def test_list_of_stock_codes_dklines(self):
        stock_codes = ['000001', 'sh000001']
        result = self.source.dklines(stock_codes, 'd', 10)
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestEmFunctions('test_list_of_stock_codes_dklines'))
    unittest.TextTestRunner().run(suite)
