import unittest
from stockrt import rtsource

class TestSinaFunctions(unittest.TestCase):
    source = rtsource('sina')
    def test_get_market_stock_count(self):
        count = self.source.get_market_stock_count()
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    def test_single_stock_quotes(self):
        stock_code = '603390'
        result = self.source.quotes(stock_code)
        self.assertIsInstance(result, dict)
        stock_data = result.get(stock_code)
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

    def test_single_stock_tlines(self):
        stock_codes = '600530'
        result = self.source.tlines(stock_codes)
        self.assertIsInstance(result, dict)

    def test_list_of_stock_codes_tlines(self):
        stock_codes = ['000001', 'sh000001']
        result = self.source.tlines(stock_codes)
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

    def test_get_stock_list(self):
        result = self.source.stock_list(market='all')
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for data in result:
            self.assertIsInstance(data, dict)
            self.assertIn('name', data)
            self.assertIn('close', data)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestSinaFunctions('test_get_stock_list'))
    unittest.TextTestRunner().run(suite)
    # unittest.main()
