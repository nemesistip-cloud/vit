import unittest

from vit_protocol.application import (
    ApplicationManifest,
    ApplicationManifestError,
    m24_reference_manifest,
    validate_manifest,
)


class VitApplicationManifestTests(unittest.TestCase):
    def test_m24_uses_shared_capabilities(self):
        manifest = m24_reference_manifest().to_dict()
        self.assertEqual(manifest["dependencies"]["chain"], "7764")
        self.assertIn("wallet.transfer", manifest["permissions"])
        self.assertIn("proof.verify", manifest["permissions"])

    def test_invalid_manifest_is_rejected(self):
        manifest = ApplicationManifest(
            app_id="bad",
            developer_id="dev:owner",
            version="1.0.0",
            account_id="acct:app",
            permissions=("wallet.read",),
            dependencies={},
            resource_limits={},
        )
        with self.assertRaises(ApplicationManifestError):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
