import zipfile
import sys

ts4script_path = "dist/HashStratum_RigManager_simocoin_network.ts4script"

with zipfile.ZipFile(ts4script_path, "r") as zf:
    namelist = zf.namelist()
    print("Files in archive:")
    for name in namelist:
        print(" -", name)
        assert name.startswith("simocoin_network/"), f"Invalid root layout: {name}"
        if name.endswith(".pyc"):
            data = zf.read(name)
            magic = data[:4]
            assert magic == b'\x42\r\r\n', f"Invalid magic bytes in {name}: {magic}"

print("\n[TEST-01 & INV-06 PASSED] All files start with 'simocoin_network/' and have Python 3.7 magic bytes b'\\x42\\r\\r\\n' (3394).")
