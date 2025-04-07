import os
import json

def build_tree(startpath):
    tree = {}
    for item in os.listdir(startpath):
        path = os.path.join(startpath, item)
        if os.path.isdir(path):
            tree[item] = build_tree(path)
        else:
            tree[item] = None  # None indicates a file
    return tree

# Set the starting directory
start_dir = os.getcwd()

# Build the structure
directory_structure = build_tree(start_dir)

# Save it as a JSON file
with open("directory_structure.json", "w") as f:
    json.dump(directory_structure, f, indent=4)

print("✅ Directory structure saved to directory_structure.json")
