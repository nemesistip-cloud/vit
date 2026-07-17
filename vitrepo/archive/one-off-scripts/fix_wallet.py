import sys

path = 'frontend/src/pages/wallet.tsx'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'if (!wallet) return null;' in line:
        new_lines.append('  if (!wallet) {\n')
        new_lines.append('    return (\n')
        new_lines.append('      <div className=\"min-h-screen flex flex-col items-center justify-center p-4 text-center\">\n')
        new_lines.append('        <div className=\"text-4xl mb-4\">🔐</div>\n')
        new_lines.append('        <h2 className=\"text-xl font-bold mb-2\">Wallet Protection Layer</h2>\n')
        new_lines.append('        <p className=\"text-muted-foreground text-sm max-w-xs mb-6\">\n')
        new_lines.append('          Unable to load wallet data. Please ensure you are logged in and have an active identity.\n')
        new_lines.append('        </p>\n')
        new_lines.append('        <div className=\"flex gap-3\">\n')
        new_lines.append('          <Button onClick={() => window.location.reload()} variant=\"outline\">Retry</Button>\n')
        new_lines.append('          <Button onClick={() => window.location.href = \"/\"}>Back Home</Button>\n')
        new_lines.append('        </div>\n')
        new_lines.append('      </div>\n')
        new_lines.append('    );\n')
        new_lines.append('  }\n')
    else:
        new_lines.append(line)

with open(path, 'w') as f:
    f.writelines(new_lines)
