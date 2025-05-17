import unittest
from stockrt.sources.rtbase import rtbase

class TestGetFullcodeFunction(unittest.TestCase):

    def test_stock_code_with_prefix(self):
        self.assertEqual(rtbase.get_fullcode("sh123456"), "sh123456")
        self.assertEqual(rtbase.get_fullcode("sz123456"), "sz123456")
        self.assertEqual(rtbase.get_fullcode("bj123456"), "bj123456")

    def test_stock_code_without_prefix(self):
        self.assertEqual(rtbase.get_fullcode("123456"), "sz123456")

    def test_stock_code_with_invalid_prefix(self):
        with self.assertRaises(AssertionError):
            rtbase.get_fullcode("abc123456")

    def test_stock_code_with_invalid_length(self):
        with self.assertRaises(AssertionError):
            rtbase.get_fullcode("12345")
        with self.assertRaises(AssertionError):
            rtbase.get_fullcode("1234567")

    def test_stock_code_with_non_string_input(self):
        with self.assertRaises(AssertionError):
            rtbase.get_fullcode(123456)

    def test_stock_code_with_valid_bj_head(self):
        self.assertEqual(rtbase.get_fullcode("412345"), "bj412345")

    def test_stock_code_with_valid_sh_head(self):
        self.assertEqual(rtbase.get_fullcode("512345"), "sh512345")

    def test_stock_code_with_invalid_head(self):
        self.assertEqual(rtbase.get_fullcode("012345"), "sz012345")


class TestToIntKltype(unittest.TestCase):
    def test_valid_integer_kltype(self):
        self.assertEqual(rtbase.to_int_kltype(1), 1)
        self.assertEqual(rtbase.to_int_kltype(101), 101)

    def test_valid_string_kltype(self):
        self.assertEqual(rtbase.to_int_kltype('1'), 1)
        self.assertEqual(rtbase.to_int_kltype('d'), 101)
        self.assertEqual(rtbase.to_int_kltype('wk'), 102)

    def test_invalid_string_kltype(self):
        with self.assertRaises(ValueError):
            rtbase.to_int_kltype('abc')

    def test_string_kltype_is_digit_but_not_in_validkls(self):
        self.assertEqual(rtbase.to_int_kltype('7'), 7)

    def test_non_string_non_integer_kltype(self):
        self.assertEqual(rtbase.to_int_kltype(None), 101)
        with self.assertRaises(ValueError):
            rtbase.to_int_kltype(True)


if __name__ == '__main__':
    unittest.main()

