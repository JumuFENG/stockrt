import unittest
from stockrt import rtsource


class TestClsFunctions(unittest.TestCase):
    source = rtsource('cls')

    def test_single_stock_quotes(self):
        stock_code = '600030'
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
        stock_codes = ['600030', '000001', '601398', '000002', '600519']
        result = self.source.quotes(stock_codes)
        self.assertIsInstance(result, dict)

    def test_single_stock_quotes5(self):
        stock_code = '600030'
        result = self.source.quotes5(stock_code)
        self.assertIsInstance(result, dict)

    def test_list_of_stock_codes_quotes5(self):
        stock_codes = ['600030', '000001']
        result = self.source.quotes5(stock_codes)
        self.assertIsInstance(result, dict)

    def test_single_stock_tlines(self):
        stock_code = '600030'
        result = self.source.tlines(stock_code)
        self.assertIsInstance(result, dict)

    def test_list_of_stock_codes_tlines(self):
        stock_codes = ['600030', '000001']
        result = self.source.tlines(stock_codes)
        self.assertIsInstance(result, dict)

    def test_single_stock_mklines(self):
        stock_code = '600030'
        result = self.source.mklines(stock_code, 1, 10)
        self.assertIsNone(result)

    def test_list_of_stock_codes_mklines(self):
        stock_codes = ['600030', '000001']
        result = self.source.mklines(stock_codes, 5, 10)
        self.assertIsNone(result)

    def test_single_stock_dklines(self):
        stock_code = '600030'
        result = self.source.dklines(stock_code, 'd', 10)
        self.assertIsInstance(result, dict)

    def test_list_of_stock_codes_dklines(self):
        stock_codes = ['600030', '000001']
        result = self.source.dklines(stock_codes, 'd', 10)
        self.assertIsInstance(result, dict)

    def test_signcode_generation(self):
        param = "app=CailianpressWeb&market=all&os=web&page=2&rever=1&sv=8.4.6&types=last_px,change,tr,main_fund_diff,cmc,trade_status"
        expected_signcode = "a2cd0e7449c4a2763db426a47f3edb40"
        generated_signcode = self.source.get_signcode(param)
        self.assertEqual(generated_signcode, expected_signcode)

if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestClsFunctions('test_signcode_generation'))
    unittest.TextTestRunner().run(suite)
    # unittest.main()