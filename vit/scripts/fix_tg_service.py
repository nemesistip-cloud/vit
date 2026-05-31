import sys

path = 'app/services/telegram_service.py'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
skip = 0
for i, line in enumerate(lines):
    if skip > 0:
        skip -= 1
        continue

    if 'f"✅ <b>Payment Successful!</b>' in line:
        new_lines.append('                        f"✅ <b>Payment Successful!</b>\\n\\n"\n')
        new_lines.append('                        f"You purchased {stars} Stars and received <b>{vit_amount} VITCoin</b>.\\n"\n')
        new_lines.append('                        f"Your balance has been updated."\n')
        skip = 6 # skip the broken lines
    elif 'text= (' in line and 'Welcome to VIT' in lines[i+1]:
        # Handle the other broken f-string if any
        new_lines.append(line)
    else:
        new_lines.append(line)

# Let's try a safer approach: direct replacement of the block
content = "".join(lines)
import re

# Fix payment message
content = re.sub(
    r'f"✅ <b>Payment Successful!</b>\n\n"\n\s+f"You purchased {stars} Stars and received <b>{vit_amount} VITCoin</b>.\n"\n\s+f"Your balance has been updated."',
    r'f"✅ <b>Payment Successful!</b>\\n\\n" f"You purchased {stars} Stars and received <b>{vit_amount} VITCoin</b>.\\n" f"Your balance has been updated."',
    content
)

# Fix welcome message
content = re.sub(
    r'text=\(\n\s+"👋 <b>Welcome to VIT Sports Intelligence!</b>\\n\\n"\n\s+"The VIT Mini App is now available! Tap the button below to launch it directly in Telegram.\\n\\n"\n\s+"To link your external account, visit your notification settings in the VIT web app."\n\s+\)',
    r'"text": ("👋 <b>Welcome to VIT Sports Intelligence!</b>\\n\\n" "The VIT Mini App is now available! Tap the button below to launch it directly in Telegram.\\n\\n" "To link your external account, visit your notification settings in the VIT web app.")',
    content
)

with open(path, 'w') as f:
    f.write(content)
