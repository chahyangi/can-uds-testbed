import unittest

from attacks.overload_0x22 import build_read_by_id, summarize
from attacks.session_denial import build_session_control, build_tester_present, classify_session_response


class OverloadAttackTest(unittest.TestCase):
    def test_build_read_by_id(self):
        self.assertEqual(build_read_by_id(0xF190), bytes.fromhex("22 f1 90"))

    def test_summarize_response_rate_and_latency(self):
        samples = [(True, 1.0), (True, 3.0), (False, None)]
        result = summarize(0.3, samples)
        self.assertEqual(result.sent, 3)
        self.assertEqual(result.answered, 2)
        self.assertAlmostEqual(result.response_rate, 2 / 3)
        self.assertAlmostEqual(result.avg_latency_ms, 2.0)

    def test_summarize_all_dropped(self):
        result = summarize(0.1, [(False, None), (False, None)])
        self.assertEqual(result.answered, 0)
        self.assertEqual(result.response_rate, 0.0)


class SessionDenialAttackTest(unittest.TestCase):
    def test_build_session_control(self):
        self.assertEqual(build_session_control(0x03), bytes.fromhex("10 03"))

    def test_build_tester_present(self):
        self.assertEqual(build_tester_present(), bytes.fromhex("3e 00"))

    def test_classify_granted(self):
        self.assertEqual(classify_session_response(bytes.fromhex("50 03 00 32 01 f4")), "granted")

    def test_classify_denied(self):
        self.assertEqual(classify_session_response(bytes.fromhex("7f 10 22")), "denied(nrc=0x22)")

    def test_classify_timeout(self):
        self.assertEqual(classify_session_response(None), "timeout")


if __name__ == "__main__":
    unittest.main()
