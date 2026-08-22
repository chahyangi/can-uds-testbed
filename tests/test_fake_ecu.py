import unittest

from fake_ecu import handle_request


class FakeEcuTest(unittest.TestCase):
    def test_default_session(self):
        self.assertEqual(handle_request(bytes.fromhex("10 01")), bytes.fromhex("50 01 00 32 01 f4"))

    def test_tester_present(self):
        self.assertEqual(handle_request(bytes.fromhex("3e 00")), bytes.fromhex("7e 00"))

    def test_read_data_by_identifier(self):
        self.assertEqual(handle_request(bytes.fromhex("22 f1 90")), bytes.fromhex("62 f1 90 01 02 03 04"))

    def test_unsupported_service(self):
        self.assertEqual(handle_request(bytes.fromhex("99 00")), bytes.fromhex("7f 99 11"))

    def test_invalid_length(self):
        self.assertEqual(handle_request(bytes.fromhex("10")), bytes.fromhex("7f 10 13"))


if __name__ == "__main__":
    unittest.main()
