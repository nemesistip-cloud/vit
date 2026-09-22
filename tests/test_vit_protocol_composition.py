import unittest

from vit_protocol.events import build_event, verify_event_payload
from vit_protocol.proofs import build_proof_envelope, verify_proof_envelope
from vit_protocol.serialization import deserialize_envelope, serialize_envelope


class VitProtocolCompositionTests(unittest.TestCase):
    def test_event_references_verifiable_proof_payload(self):
        payload = {"result": "home", "confidence": "0.62"}
        proof = build_proof_envelope(
            proof_type="ai_attestation",
            object_id="prediction:42",
            object_version="1",
            timestamp="2026-09-22T00:00:00Z",
            signer="did:vit:ai",
            payload=payload,
            result=payload,
        )
        event = build_event(
            event_type="AIInferenceCompleted",
            source="vit-ai",
            payload=proof,
            timestamp="2026-09-22T00:00:01Z",
        )
        self.assertTrue(verify_event_payload(event, proof))
        self.assertTrue(verify_proof_envelope(proof, payload)["valid"])

    def test_serialization_round_trip_is_stable(self):
        value = {"b": 2, "a": [1, 2, 3]}
        raw = serialize_envelope(value)
        self.assertEqual(deserialize_envelope(raw), value)


if __name__ == "__main__":
    unittest.main()
