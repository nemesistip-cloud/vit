import unittest

from vit_protocol.proofs import (
    ProofEnvelopeError,
    build_proof_envelope,
    verify_proof_envelope,
)


class VitProofEnvelopeTests(unittest.TestCase):
    def test_envelope_is_deterministic_and_verifiable(self):
        kwargs = {
            "proof_type": "ai_attestation",
            "object_id": "obj:prediction:42",
            "object_version": "1.0",
            "timestamp": "2026-09-22T00:00:00Z",
            "signer": "did:vit:service-ai",
            "payload": {"prediction": "home", "confidence": 0.62},
            "model_id": "ensemble",
            "model_version": "v2",
        }
        first = build_proof_envelope(**kwargs)
        second = build_proof_envelope(**kwargs)
        self.assertEqual(first, second)
        result = verify_proof_envelope(first, kwargs["payload"])
        self.assertTrue(result["valid"])
        self.assertTrue(result["payload_verified"])

    def test_tampered_payload_is_rejected(self):
        envelope = build_proof_envelope(
            proof_type="data_integrity",
            object_id="obj:1",
            object_version="1",
            timestamp="2026-09-22T00:00:00Z",
            signer="did:vit:storage",
            payload={"content": "original"},
        )
        with self.assertRaises(ProofEnvelopeError):
            verify_proof_envelope(envelope, {"content": "tampered"})

    def test_missing_required_fields_are_rejected(self):
        with self.assertRaises(ProofEnvelopeError):
            verify_proof_envelope({"proof_id": "proof:bad"})


if __name__ == "__main__":
    unittest.main()
