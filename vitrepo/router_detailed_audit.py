import os
import re

def get_subsystem_owner(file_path):
    if "modules" in file_path:
        return file_path.split("modules/")[1].split("/")[0]
    if "api/routes/explorer" in file_path:
        return "explorer"
    if "api/routes" in file_path:
        return "core_api"
    return "unknown"

def audit_routers():
    main_file = "main.py"
    with open(main_file, 'r') as f:
        main_content = f.read()

    router_files = []
    # Search in app/api/routes
    for root, dirs, files in os.walk("app/api/routes"):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                router_files.append(os.path.join(root, file))

    # Search in app/modules
    for root, dirs, files in os.walk("app/modules"):
        for file in files:
            if file.endswith("routes.py") or file.endswith("router.py"):
                router_files.append(os.path.join(root, file))

    inventory = []
    prefixes = {}

    for r_file in router_files:
        with open(r_file, 'r') as f:
            content = f.read()

        router_match = re.search(r"router = APIRouter\((.*?)\)", content, re.DOTALL)
        if router_match:
            params = router_match.group(1)
            prefix_match = re.search(r'prefix=["\'](.*?)["\']', params)
            prefix = prefix_match.group(1) if prefix_match else "/"

            # Check registration
            file_base = os.path.basename(r_file).replace(".py", "")
            is_mounted = (f"{file_base}_router" in main_content or
                          f"app.include_router({file_base}_router" in main_content or
                          f"from {r_file.replace('/', '.').replace('.py', '')} import router" in main_content or
                          (file_base == "routes" and f"from {os.path.dirname(r_file).replace('/', '.')} import router" in main_content))

            # Additional check for common patterns in main.py
            if not is_mounted:
                # Check for explicit imports of specific routers
                search_term = r_file.replace("app/", "").replace(".py", "").replace("/", ".")
                if search_term in main_content:
                    is_mounted = True

            subsystem = get_subsystem_owner(r_file)

            duplicate = False
            if prefix != "/":
                if prefix in prefixes:
                    duplicate = True
                else:
                    prefixes[prefix] = r_file

            inventory.append({
                "file": r_file,
                "prefix": prefix,
                "mounted": is_mounted,
                "subsystem": subsystem,
                "duplicate": duplicate,
                "deprecated": "legacy" in r_file or "archive" in r_file
            })

    print("| File | Prefix | Mounted | Subsystem | Reachable | Duplicate | Deprecated | Confidence |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for item in inventory:
        reachable = item['mounted']
        confidence = "High"
        print(f"| {item['file']} | {item['prefix']} | {item['mounted']} | {item['subsystem']} | {reachable} | {item['duplicate']} | {item['deprecated']} | {confidence} |")

if __name__ == "__main__":
    audit_routers()
