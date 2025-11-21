import unittest
import time
from stockrt import rtsource
from unittest.mock import patch
from stockrt.sources.eastmoney import Em


class TestEmFunctions(unittest.TestCase):
    source = rtsource('em')
    def test_single_stock_quotes(self):
        stock_code = '400174'
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
        stock_codes = '603122'
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

    def test_get_em_cookie(self):
        cookie = self.source.get_em_cookie()
        self.assertIsInstance(cookie, str)
        self.assertGreater(len(cookie), 0)
        cookie2 = self.source.get_em_cookie()
        self.assertEqual(cookie, cookie2)

    def test_get_stock_list(self):
        result = self.source.stock_list(market='all')
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result['all'], list)
        result = result['all']
        self.assertGreater(len(result), 0)
        for data in result:
            self.assertIsInstance(data, dict)
            self.assertIn('name', data)
            self.assertIn('close', data)


class TestEmCookie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cookie_data = [
            {'cookie': 'cookie1', 'timestamp': time.time(), 'used': 0, 'total_used': 0},
            {'cookie': 'cookie2', 'timestamp': time.time() - 600, 'used': 0, 'total_used': 0},
            {'cookie': 'cookie3', 'timestamp': time.time() - 600, 'used': 0, 'total_used': 0},
        ]
        Em.cookies = cls.cookie_data

    @classmethod
    def tearDownClass(cls):
        Em.cookies = []

    def test_get_cookie_with_available_cookie(self):
        cookie = Em.get_cookie()
        self.assertIn(cookie, [c['cookie'] for c in Em.cookies])
        self.assertEqual(cookie, Em.cookies[0]['cookie'])

    @patch('stockrt.sources.eastmoney.EmCookie.generate_cookie', return_value='new_cookie')
    def test_get_cookie_with_no_available_cookie(self, mock_generate):
        for cookie in Em.cookies:
            cookie['timestamp'] = time.time()
            cookie['used'] = 500
        cookie = Em.get_cookie()
        self.assertIn(cookie, [c['cookie'] for c in Em.cookies])
        self.assertEqual(cookie, Em.cookies[-1]['cookie'])

    def test_get_cookie_with_expired_cookie(self):
        Em.cookies = [c for c in Em.cookies if c['used'] < 499]
        for cookie in Em.cookies:
            cookie['timestamp'] = time.time() - 600
            cookie['used'] = 0
        cookie = Em.get_cookie()
        self.assertIn(cookie, [c['cookie'] for c in Em.cookies])

    def test_cookie_usage_increment(self):
        initial_used_counts = [c['used'] for c in Em.cookies]
        initial_total_used_counts = [c['total_used'] for c in Em.cookies]
        cookie = Em.get_cookie()
        for i, c in enumerate(Em.cookies):
            if c['cookie'] == cookie:
                self.assertEqual(c['used'], initial_used_counts[i] + 1)
                self.assertEqual(c['total_used'], initial_total_used_counts[i] + 1)
            else:
                self.assertEqual(c['used'], initial_used_counts[i])

    @patch('stockrt.sources.eastmoney.EmCookie.generate_cookie', return_value='new_cookie')
    def test_cookie_total_usage_overload(self, mock_generate):
        for cookie in Em.cookies:
            cookie['total_used'] = 50000
        old_cookies = [c['cookie'] for c in Em.cookies]
        cookie = Em.get_cookie()
        self.assertNotIn(cookie, old_cookies)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestEmFunctions('test_single_stock_dklines'))
    unittest.TextTestRunner().run(suite)
    # unittest.main()