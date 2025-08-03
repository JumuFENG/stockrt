import unittest
from stockrt import rtsource

class TestEmFunctions(unittest.TestCase):
    source = rtsource('em')
    def test_single_stock_quotes(self):
        stock_code = '688313'
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

    def test_single_stock_quotes5(self):
        stock_codes = '688313'
        result = self.source.quotes5(stock_codes)
        self.assertIsInstance(result, dict)

    def test_list_of_stock_codes_quotes5(self):
        stock_codes = ['000001', 'sh000001']
        result = self.source.quotes5(stock_codes)
        self.assertIsInstance(result, dict)

    def test_single_stock_tlines(self):
        stock_codes = '000001'
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

    def test_single_stock_fklines(self):
        stock_codes = 'sh000001'
        result = self.source.fklines(stock_codes, 'd', 0)
        self.assertIsInstance(result, dict)
        klines = result.get(stock_codes)
        self.assertEqual(klines[0][0], '1990-12-19')


if __name__ == '__main__':
    # suite = unittest.TestSuite()
    # suite.addTest(TestEmFunctions('test_single_stock_quotes5'))
    # unittest.TextTestRunner().run(suite)
    # unittest.main()
    s = rtsource('em')
    kl = s.klines('513050', 15, 64)['513050']
    for k in kl:
        print([k[0], k[1], k[2], k[3], k[4], k[8]])

    # print(kl)