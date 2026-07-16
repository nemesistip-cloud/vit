import os
import re

def audit_routers():
    routes_dir = "app/api/routes"
    main_file = "main.py"

    with open(main_file, 'r') as f:
        main_content = f.read()

    router_files = []
    for root, dirs, files in os.walk(routes_dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                router_files.append(os.path.join(root, file))

    inventory = []
    for r_file in router_files:
        with open(r_file, 'r') as f:
            content = f.read()

        router_match = re.search(r"router = APIRouter\((.*?)\)", content, re.DOTALL)
        if router_match:
            params = router_match.group(1)
            prefix_match = re.search(r'prefix=["\'](.*?)["\']', params)
            prefix = prefix_match.group(1) if prefix_match else "/"

            # Check if mounted in main.py
            file_base = os.path.basename(r_file).replace(".py", "")
            is_mounted = f"{file_base}_router" in main_content or f"from {r_file.replace('/', '.').replace('.py', '')} import router" in main_content

            inventory.append({
                "file": r_file,
                "prefix": prefix,
                "mounted": is_mounted
            })

    for item in inventory:
        print(f"File: {item['file']}, Prefix: {item['prefix']}, Mounted: {item['mounted']}")

if __name__ == "__main__":
    audit_routers()
