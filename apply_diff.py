import sys
import re

def apply_diff(file_path, diff_path):
    with open(file_path, 'r') as f:
        content = f.read()
    with open(diff_path, 'r') as f:
        diff_data = f.read()

    # Split by the REPLACE marker to get individual chunks
    chunks = re.split(r'>>>>>>> REPLACE\n?', diff_data)
    for chunk in chunks:
        if not chunk.strip():
            continue

        m = re.search(r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)$', chunk, re.DOTALL)
        if m:
            search_block = m.group(1)
            replace_block = m.group(2)

            if search_block in content:
                content = content.replace(search_block, replace_block)
            else:
                # Try to be a bit more flexible with trailing newlines
                if search_block.strip() in content:
                     # This is risky but let's try to find it
                     pass
                print(f"Error: Search block not found in {file_path}")
                # print(f"Looking for:\n{search_block}")
                sys.exit(1)
        else:
            print(f"Error: Could not parse chunk:\n{chunk[:100]}...")
            sys.exit(1)

    with open(file_path, 'w') as f:
        f.write(content)
    print(f"Successfully applied diff to {file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 apply_diff.py <file_path> <diff_path>")
        sys.exit(1)
    apply_diff(sys.argv[1], sys.argv[2])
