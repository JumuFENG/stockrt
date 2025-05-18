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
        self.assertEqual(rtbase.get_fullcode("830946"), "bj830946")
        self.assertEqual(rtbase.get_fullcode("870436"), "bj870436")
        self.assertEqual(rtbase.get_fullcode("920128"), "bj920128")
        self.assertEqual(rtbase.get_fullcode("430017"), "bj430017")


    def test_stock_code_with_valid_sh_head(self):
        self.assertEqual(rtbase.get_fullcode("512345"), "sh512345")
        self.assertEqual(rtbase.get_fullcode("688755"), "sh688755")
        self.assertEqual(rtbase.get_fullcode("600610"), "sh600610")
        self.assertEqual(rtbase.get_fullcode("518880"), "sh518880")
        self.assertEqual(rtbase.get_fullcode("513520"), "sh513520")

    def test_stock_code_with_valid_sz_head(self):
        self.assertEqual(rtbase.get_fullcode("000001"), "sz000001")
        self.assertEqual(rtbase.get_fullcode("300002"), "sz300002")
        self.assertEqual(rtbase.get_fullcode("161129"), "sz161129")
        self.assertEqual(rtbase.get_fullcode("159915"), "sz159915")

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

