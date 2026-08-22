import unittest

from stateful_ecu import SessionState


class SessionStateTest(unittest.TestCase):
    def test_extended_session_grant(self):
        state = SessionState()
        resp = state.handle(bytes.fromhex("10 03"), "attacker", now=0.0)
        self.assertEqual(resp, bytes.fromhex("50 03 00 32 01 f4"))
        self.assertEqual(state.holder, "attacker")

    def test_second_tester_denied_while_held(self):
        state = SessionState()
        state.handle(bytes.fromhex("10 03"), "attacker", now=0.0)
        resp = state.handle(bytes.fromhex("10 01"), "legit", now=1.0)
        self.assertEqual(resp, bytes.fromhex("7f 10 22"))

    def test_tester_present_refreshes_holder_only(self):
        state = SessionState(s3_timeout=5.0)
        state.handle(bytes.fromhex("10 03"), "attacker", now=0.0)
        state.handle(bytes.fromhex("3e 00"), "attacker", now=4.0)
        # still within S3 of the refreshed timestamp, held by attacker
        resp = state.handle(bytes.fromhex("10 01"), "legit", now=8.0)
        self.assertEqual(resp, bytes.fromhex("7f 10 22"))

    def test_session_released_after_s3_timeout(self):
        state = SessionState(s3_timeout=5.0)
        state.handle(bytes.fromhex("10 03"), "attacker", now=0.0)
        resp = state.handle(bytes.fromhex("10 01"), "legit", now=10.0)
        self.assertEqual(resp, bytes.fromhex("50 01 00 32 01 f4"))
        self.assertIsNone(state.holder)

    def test_holder_can_release_by_requesting_default(self):
        state = SessionState()
        state.handle(bytes.fromhex("10 03"), "attacker", now=0.0)
        state.handle(bytes.fromhex("10 01"), "attacker", now=1.0)
        resp = state.handle(bytes.fromhex("10 03"), "legit", now=1.1)
        self.assertEqual(resp, bytes.fromhex("50 03 00 32 01 f4"))

    def test_read_data_by_identifier_ignores_session(self):
        state = SessionState()
        state.handle(bytes.fromhex("10 03"), "attacker", now=0.0)
        resp = state.handle(bytes.fromhex("22 f1 90"), "legit", now=0.5)
        self.assertEqual(resp, bytes.fromhex("62 f1 90 01 02 03 04"))


if __name__ == "__main__":
    unittest.main()
