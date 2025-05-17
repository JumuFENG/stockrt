import unittest
from stockrt.wrapper import FetchWrapper

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

if __name__ == '__main__':
    unittest.main()
