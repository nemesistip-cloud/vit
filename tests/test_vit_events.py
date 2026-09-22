import unittest

from vit_protocol.events import EventEnvelopeError, build_event, verify_event_payload


class VitEventEnvelopeTests(unittest.TestCase):
    def test_event_payload_verifies(self):
        payload = {"payment_id": "pay:1", "amount": "10"}
        event = build_event(
            event_type="PaymentConfirmed",
            source="vit-chain",
            payload=payload,
            timestamp="2026-09-22T00:00:00Z",
            block_reference={"height": 12, "tx_hash": "0xabc"},
        )
        self.assertTrue(verify_event_payload(event, payload))
        self.assertFalse(verify_event_payload(event, {"payment_id": "pay:2"}))

    def test_unknown_event_is_rejected(self):
        with self.assertRaises(EventEnvelopeError):
            build_event(
                event_type="UnknownEvent",
                source="app:m24",
                payload={},
                timestamp="2026-09-22T00:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
