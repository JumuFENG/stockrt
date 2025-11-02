import unittest
from stockrt import rtsource

class TestXueqiuFunctions(unittest.TestCase):
    source = rtsource('xq')
    def test_single_stock_quotes(self):
        stock_code = '518880'
        result = self.source.quotes(stock_code)
        self.assertIsInstance(result, dict)
        stock_data = result.get(stock_code)
        self.assertIsNotNone(stock_data)
        self.assertIsInstance(stock_data, dict)
        required_keys = ['price', 'change', 'lclose', 'volume', 'amount']
        for key in required_keys:
            self.assertIn(key, stock_data)
            self.assertIsNotNone(stock_data[key])

    def test_list_of_stock_codes_quotes(self):
        stock_codes = ['sh000001', 'sh000006', '399001', '000001', '600530']
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

    def test_stock_list_retrieval(self):
        market = 'all'
        result = self.source.stock_list(market)
        self.assertIsInstance(result, dict)
        self.assertIn(market, result)
        self.assertIsInstance(result[market], list)
        self.assertGreater(len(result[market]), 0)
        for stock in result[market]:
            self.assertIn('code', stock)
            self.assertIn('name', stock)
            self.assertIn('close', stock)
            self.assertIn('change', stock)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestXueqiuFunctions('test_stock_list_retrieval'))
    unittest.TextTestRunner().run(suite)
    # unittest.main()
