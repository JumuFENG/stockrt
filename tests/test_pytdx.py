import unittest
from stockrt import rtsource

class TestTdxFunctions(unittest.TestCase):
    source = rtsource('tdx')
    def tearDown(self):
        [ c.disconnect() for c in self.source.clients]

    def test_single_stock_quotes(self):
        stock_code = '688313'
        result = self.source.quotes(stock_code)
        self.assertIsInstance(result, dict)
        stock_data = result.get(stock_code)
        self.assertIsNotNone(stock_data)
        self.assertIsInstance(stock_data, dict)
        required_keys = ['price', 'change', 'high', 'low', 'open', 'lclose', 'volume', 'amount']
        for key in required_keys:
            self.assertIn(key, stock_data)
            self.assertIsNotNone(stock_data[key])

    def test_list_of_stock_codes_quotes(self):
        stock_codes = ['000001', '000002']
        result = self.source.quotes(stock_codes)
        self.assertIsInstance(result, dict)

    def test_single_stock_quotes5(self):
        stock_codes = '688313'
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

    def test_single_stock_transactions(self):
        stock_codes = '000001'
        result = self.source.transactions(stock_codes, None)
        self.assertIsInstance(result, dict)

    def test_single_stock_transaction_date(self):
        stock_codes = '000001'
        result = self.source.transactions(stock_codes, '2025-12-01')
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestTdxFunctions('test_list_of_stock_codes_mklines'))
    # suite.addTest(TestTdxFunctions('test_single_stock_transaction_date'))
    unittest.TextTestRunner().run(suite)
    # unittest.main()
