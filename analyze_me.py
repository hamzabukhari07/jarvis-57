import os
from collections import defaultdict

root = r'.'
print("=== .kilo directories ===")
kilo_sizes = []
for dirpath, dirnames, filenames in os.walk(root):
    parts = dirpath.split(os.sep)
    if '.kilo' in parts:
        sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fs in os.walk(dirpath) for f in fs if os.path.isfile(os.path.join(dp, f)))
        kilo_sizes.append((dirpath, sz))
for d, sz in sorted(kilo_sizes, key=lambda x: -x[1]):
    rel = d.replace(root, '.')
    print(f"  {rel:65s} {sz/1048576:.2f} MB")
print(f"  TOTAL .kilo: {sum(s for _, s in kilo_sizes)/1048576:.2f} MB")

print("\n=== node_modules directories ===")
nm_sizes = []
for dirpath, dirnames, filenames in os.walk(root):
    parts = dirpath.split(os.sep)
    if 'node_modules' in parts:
        sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fs in os.walk(dirpath) for f in fs if os.path.isfile(os.path.join(dp, f)))
        nm_sizes.append((dirpath, sz))
total_node = 0
for d, sz in sorted(nm_sizes, key=lambda x: -x[1]):
    rel = d.replace(root, '.')
    total_node += sz
    print(f"  {rel:65s} {sz/1048576:.2f} MB")
print(f"  TOTAL node_modules: {total_node/1048576:.2f} MB")

print("\n=== Largest files (>5MB) ===")
big_files = []
for dirpath, dirnames, filenames in os.walk(root):
    parts = dirpath.split(os.sep)
    if '.venv' in parts or '.git' in parts:
        continue
    for f in filenames:
        fp = os.path.join(dirpath, f)
        try:
            sz = os.path.getsize(fp)
            if sz > 5 * 1024 * 1024:
                big_files.append((fp, sz))
        except:
            pass
for fp, sz in sorted(big_files, key=lambda x: -x[1]):
    print(f"  {fp:70s} {sz/1048576:.2f} MB")
