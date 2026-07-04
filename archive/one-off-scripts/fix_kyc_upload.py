import re

with open('app/modules/kyc/routes.py', 'r') as f:
    content = f.read()

# Add document_data to KYCSubmitRequest
content = content.replace('selfie_data:     Optional[dict] = None', 'selfie_data:     Optional[dict] = None\n    document_data:   Optional[dict] = None')

# Update submit_kyc to handle document_data and use Tachyon for storage
# I'll find the submission creation block
old_submission_init = r'submission = KYCSubmission\(.*?risk_flags      = result\["risk_flags"\],\n    \)'
new_submission_init = """submission = KYCSubmission(
        user_id         = current_user.id,
        full_name       = body.full_name,
        date_of_birth   = body.date_of_birth,
        nationality     = body.nationality,
        document_type   = body.document_type,
        document_number = body.document_number.strip().upper(),
        address         = body.address,
        selfie_data     = body.selfie_data,
        status          = status,
        risk_score      = result["risk_score"],
        risk_level      = result["risk_level"],
        rule_checks     = result["rule_checks"],
        risk_flags      = result["risk_flags"],
    )

    # SEC-09: Store KYC artifacts in Tachyon Decentralized Storage
    from app.services.tachyon_client import tachyon_client
    if body.selfie_data and body.selfie_data.get("image"):
        try:
            import base64
            img_data = body.selfie_data["image"]
            if "," in img_data: img_data = img_data.split(",")[1]
            content_bytes = base64.b64decode(img_data)
            fid = await tachyon_client.upload_bytes(content_bytes, f"kyc_selfie_{current_user.id}.jpg")
            submission.selfie_data["tachyon_id"] = fid
        except Exception:
            pass

    if body.document_data and body.document_data.get("image"):
        try:
            import base64
            img_data = body.document_data["image"]
            if "," in img_data: img_data = img_data.split(",")[1]
            content_bytes = base64.b64decode(img_data)
            fid = await tachyon_client.upload_bytes(content_bytes, f"kyc_doc_{current_user.id}.jpg")
            submission.rule_checks["document_tachyon_id"] = fid
        except Exception:
            pass"""

content = re.sub(r'submission = KYCSubmission\(.*?risk_flags      = result\["risk_flags"\],.*? \)', new_submission_init, content, flags=re.DOTALL)

with open('app/modules/kyc/routes.py', 'w') as f:
    f.write(content)
