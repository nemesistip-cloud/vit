import os

def fix_file(path, replacements):
    if not os.path.exists(path):
        return
    with open(path, 'r') as f:
        content = f.read()

    new_content = content
    for search, replace in replacements:
        new_content = new_content.replace(search, replace)

    if new_content != content:
        with open(path, 'w') as f:
            f.write(new_content)
        print(f"Fixed {path}")

# Dashboard
fix_file('frontend/src/pages/dashboard.tsx', [
    ('rounded-lg p-3 border border-border/30', 'rounded-xl p-3.5 border border-border/40 hover:shadow-md backdrop-blur-sm'),
    ('bg-background/40 rounded-lg p-3.5 border border-border/40', 'bg-background/40 rounded-xl p-3.5 border border-border/40 hover:shadow-md backdrop-blur-sm'),
])

# Assistant
fix_file('frontend/src/pages/assistant.tsx', [
    ('rounded-lg px-3.5 py-2.5', 'rounded-xl px-4 py-3 shadow-sm'),
    ('Card className="overflow-hidden', 'Card className="overflow-hidden rounded-2xl border-border/50 shadow-2xl bg-card/60 backdrop-blur-md'),
])

# PremiumMatchCard
fix_file('frontend/src/components/PremiumMatchCard.tsx', [
    ('rounded-xl border', 'rounded-2xl border border-border/50 shadow-xl hover:shadow-2xl transition-all bg-card/60 backdrop-blur-md'),
])

# Offerwall
fix_file('frontend/src/pages/offerwall.tsx', [
    ('rounded-lg border', 'rounded-2xl border border-border/50 hover:shadow-xl bg-card/60 backdrop-blur-md'),
])
