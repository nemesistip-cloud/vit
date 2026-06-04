import sys

with open("app/auth/routes.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "idinfo = id_token.verify_oauth2_token(" in line:
        new_lines.append("        # Attempt verification with standard Google library first\n")
        new_lines.append("        try:\n")
        new_lines.append("            idinfo = id_token.verify_oauth2_token(\n")
        new_lines.append("                body.id_token, google_requests.Request(), google_client_id\n")
        new_lines.append("            )\n")
        new_lines.append("        except Exception as e:\n")
        new_lines.append("            # Fallback: Try verifying via Firebase if standard verification fails\n")
        new_lines.append("            # (Useful for tokens issued via Firebase Auth)\n")
        new_lines.append("            from app.auth.firebase_utils import verify_firebase_id_token\n")
        new_lines.append("            decoded = verify_firebase_id_token(body.id_token)\n")
        new_lines.append("            if not decoded:\n")
        new_lines.append("                raise e\n")
        new_lines.append("            idinfo = decoded\n")
        new_lines.append("            # Map firebase fields to expected idinfo fields\n")
        new_lines.append("            idinfo[\"sub\"] = idinfo.get(\"sub\") or idinfo.get(\"user_id\")\n")
        skip = True
        continue

    if skip:
        if "        )" in line:
            skip = False
        continue

    new_lines.append(line)

with open("app/auth/routes.py", "w") as f:
    f.writelines(new_lines)
