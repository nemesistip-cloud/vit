import os
import re

files_to_delete = [
    "frontend/src/pages/jules-prompt.tsx",
    "frontend/src/pages/iq-test.tsx",
    "frontend/src/pages/wrapped.tsx",
    "frontend/src/pages/stadium-mode.tsx",
    "frontend/src/pages/oracle-mic.tsx",
    "frontend/src/pages/discipline-coach.tsx",
    "frontend/src/pages/quality-feed.tsx",
    "frontend/src/pages/debate-markets.tsx",
    "frontend/src/pages/bet-rooms.tsx",
    "frontend/src/pages/prophecy-chain.tsx",
    "frontend/src/pages/node-network.tsx",
]

for f in files_to_delete:
    if os.path.exists(f):
        os.remove(f)
        print(f"Deleted {f}")

# Update App.tsx
with open("frontend/src/App.tsx", "r") as f:
    content = f.read()

for f in files_to_delete:
    basename = os.path.basename(f).replace(".tsx", "")
    # Component name is usually PascalCase
    component_name = "".join([x.capitalize() for x in basename.split("-")])
    if "Iq" in component_name: component_name = component_name.replace("Iq", "IQ")
    if "Kyc" in component_name: component_name = component_name.replace("Kyc", "KYC")

    # Try to remove import and route
    # Import: import JulesPromptPage from "./pages/jules-prompt";
    # Actually, the file uses lazy loading? No, it looks like normal imports might be used or they are in the same file.
    # Looking at App.tsx again...

    # Remove Route
    pattern = r'<Route path="/' + basename.replace("jules-prompt", "jules-prompt") + r'".*?/>'
    # Handle variations in path names
    if basename == "iq-test":
        content = re.sub(r'<Route path="/iq-test".*?/>', '', content)
    elif basename == "stadium-mode":
        content = re.sub(r'<Route path="/stadium".*?/>', '', content)
    elif basename == "oracle-mic":
        content = re.sub(r'<Route path="/oracle-mic".*?/>', '', content)
    elif basename == "quality-feed":
        content = re.sub(r'<Route path="/quality-feed".*?/>', '', content)
    elif basename == "debate-markets":
        content = re.sub(r'<Route path="/debates".*?/>', '', content)
    elif basename == "bet-rooms":
        content = re.sub(r'<Route path="/rooms".*?/>', '', content)
    elif basename == "node-network":
        content = re.sub(r'<Route path="/node-network".*?/>', '', content)
    else:
        content = re.sub(r'<Route path="/' + basename + r'".*?/>', '', content)

with open("frontend/src/App.tsx", "w") as f:
    f.write(content)

# Update layout.tsx (NAV_GROUPS)
with open("frontend/src/components/layout.tsx", "r") as f:
    content = f.read()

for f in files_to_delete:
    basename = os.path.basename(f).replace(".tsx", "")
    path = "/" + basename
    if basename == "stadium-mode": path = "/stadium"
    if basename == "debate-markets": path = "/debates"
    if basename == "bet-rooms": path = "/rooms"

    # Remove from NAV_GROUPS
    # { name: "...", href: "/...", icon: ... },
    content = re.sub(r'\{\s*name: "[^"]+",\s*href: "' + path + r'",\s*icon: [^ }]+\s*\},?', '', content)

with open("frontend/src/components/layout.tsx", "w") as f:
    f.write(content)
