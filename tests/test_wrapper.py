import unittest
from stockrt.wrapper import FetchWrapper, rtsource

class TestWrapper(unittest.TestCase):

    def test_valid_source_names(self):
        valid_sources = ['sina', 'qq', 'tencent', 'em', 'eastmoney']
        for source in valid_sources:
            data_source = FetchWrapper.get_data_source(source)
            self.assertIsNotNone(data_source)

    def test_invalid_source_names(self):
        invalid_sources = ['invalid', 'unknown', 'foo']
        for source in invalid_sources:
            with self.assertRaises(NotImplementedError):
                FetchWrapper.get_data_source(source)

    def test_duplicate_source_names(self):
        data_source1 = FetchWrapper.get_data_source('sina')
        data_source2 = FetchWrapper.get_data_source('sina')
        self.assertEqual(data_source1, data_source2)

    def test_case_insensitivity(self):
        data_source1 = FetchWrapper.get_data_source('SINA')
        data_source2 = FetchWrapper.get_data_source('sina')
        self.assertEqual(data_source1, data_source2)


class TestSourcesDataMatch(unittest.TestCase):
    sourcekeys = ['sina', 'qq', 'em']
    sources = [rtsource(k) for k in sourcekeys]

    def test_sources_quotes_match(self):
        code = 'sh000001'
        quotes = {source_key: source.quotes(code)[code] for source_key, source in zip(self.sourcekeys, self.sources)}
        base_quote = next(iter(quotes.values()))
        price, open, high = round(base_quote['price'], 2), round(base_quote['open'], 2), round(base_quote['high'], 2)
        low, lclose = round(base_quote['low'], 2), round(base_quote['lclose'], 2)
        change, changepx = round(base_quote['change'], 4), round(base_quote['change_px'], 2)
        volume, amount = round(base_quote['volume'] / 100), round(base_quote['amount'] / 1e6)

        for source_key, squotes in quotes.items():
            msgsrc = f'source = {source_key}'
            self.assertEqual(price, round(squotes['price'], 2), msg=msgsrc)
            self.assertEqual(open, round(squotes['open'], 2), msg=msgsrc)
            self.assertEqual(high, round(squotes['high'], 2), msg=msgsrc)
            self.assertEqual(low, round(squotes['low'], 2), msg=msgsrc)
            self.assertEqual(lclose, round(squotes['lclose'], 2), msg=msgsrc)
            self.assertEqual(volume, round(squotes['volume'] / 100), msg=msgsrc)
            self.assertEqual(amount, round(squotes['amount'] / 1e6), msg=msgsrc)
            self.assertAlmostEqual(change, round(squotes['change'], 4), msg=msgsrc)
            self.assertAlmostEqual(changepx, round(squotes['change_px'], 2), msg=msgsrc)

    def test_sources_quotes5_match(self):
        code = '000001'
        quotes = {source_key: source.quotes5(code)[code] for source_key, source in zip(self.sourcekeys, self.sources)}
        base_quote = next(iter(quotes.values()))
        price, bid1, bid2, bid5 = round(base_quote['price'], 2), round(base_quote['bid1'], 2), round(base_quote['bid2'], 2), round(base_quote['bid5'], 2)
        bid1_v, bid2_v, bid5_v = round(base_quote['bid1_volume'] / 100), round(base_quote['bid2_volume'] / 100), round(base_quote['bid5_volume'] / 100)

        for source_key, squotes in quotes.items():
            msgsrc = f'source = {source_key}'
            self.assertEqual(price, round(squotes['price'], 2), msg=msgsrc)
            self.assertEqual(bid1, round(squotes['bid1'], 2), msg=msgsrc)
            self.assertEqual(bid2, round(squotes['bid2'], 2), msg=msgsrc)
            self.assertEqual(bid5, round(squotes['bid5'], 2), msg=msgsrc)
            self.assertEqual(bid1_v, round(squotes['bid1_volume'] / 100), msg=msgsrc)
            self.assertEqual(bid2_v, round(squotes['bid2_volume'] / 100), msg=msgsrc)
            self.assertEqual(bid5_v, round(squotes['bid5_volume'] / 100), msg=msgsrc)

    def test_sources_tlines_match(self):
        code = '000001'
        tlines = {source_key: source.tlines(code)[code] for source_key, source in zip(self.sourcekeys, self.sources)}
        lasttline = next(iter(tlines.values()))[-1]
        time = lasttline['time']
        price = round(lasttline['price'], 2)
        volume = round(lasttline['volume'] / 100)
        amount = round(lasttline['amount'] / 1e6)
        for source_key, squotes in tlines.items():
            msgsrc = f'source = {source_key}'
            self.assertEqual(time, squotes[-1]['time'], msg=msgsrc)
            self.assertEqual(price, round(squotes[-1]['price'], 2), msg=msgsrc)
            self.assertEqual(volume, round(squotes[-1]['volume'] / 100), msg=msgsrc)
            self.assertEqual(amount, round(squotes[-1]['amount'] / 1e6), msg=msgsrc)

    def test_sources_mklines_match(self):
        code = '000001'
        mklines = {source_key: source.mklines(code, 5, 48)[code] for source_key, source in zip(self.sourcekeys, self.sources)}
        lastmkline = next(iter(mklines.values()))[-1]
        time = lastmkline['time']
        open = round(lastmkline['open'], 2)
        close = round(lastmkline['close'], 2)
        high = round(lastmkline['high'], 2)
        low = round(lastmkline['low'], 2)
        for source_key, squotes in mklines.items():
            msgsrc = f'source = {source_key}'
            self.assertEqual(time, squotes[-1]['time'], msg=msgsrc)
            self.assertEqual(open, round(squotes[-1]['open'], 2), msg=msgsrc)
            self.assertEqual(close, round(squotes[-1]['close'], 2), msg=msgsrc)
            self.assertEqual(high, round(squotes[-1]['high'], 2), msg=msgsrc)
            self.assertEqual(low, round(squotes[-1]['low'], 2), msg=msgsrc)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestSourcesDataMatch('test_sources_mklines_match'))
    unittest.TextTestRunner().run(suite)
