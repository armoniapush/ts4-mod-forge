import argparse
import fnmatch
import os
import shutil
import sys
from zipfile import PyZipFile, ZIP_DEFLATED

def verify_python_version():
    major, minor = sys.version_info[:2]
    if (major, minor) != (3, 7):
        print(f"[ERROR] TS4 compiler MUST run on Python 3.7.x! Detected: Python {sys.version.split()[0]}", file=sys.stderr)
        print("[HINT] Run via the project environment: .conda-env\\python.exe tools/compiler/compiler.py ...", file=sys.stderr)
        sys.exit(1)

def compile_mod(src_dir: str, mod_name: str, dist_dir: str, creator_name: str = "Forge", devmode_parity: bool = False):
    verify_python_version()

    full_mod_name = f"{creator_name}_{mod_name}" if creator_name else mod_name
    os.makedirs(dist_dir, exist_ok=True)
    out_ts4script = os.path.join(dist_dir, f"{full_mod_name}.ts4script")

    if os.path.exists(out_ts4script):
        os.remove(out_ts4script)

    print(f"[*] Compiling '{mod_name}' (Python 3.7 bytecode)...")
    zf = PyZipFile(out_ts4script, mode='w', compression=ZIP_DEFLATED, allowZip64=True, optimize=2)

    try:
        zf.writepy(src_dir)
        print(f"[✓] Bytecode compiled and packed into: {out_ts4script}")
    finally:
        zf.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile TS4 script mod to .ts4script using Python 3.7.9 bytecode")
    parser.add_argument("--src", required=True, help="Path to mod source directory")
    parser.add_argument("--name", required=True, help="Mod name")
    parser.add_argument("--dist", default="dist", help="Output directory")
    parser.add_argument("--creator", default="Forge", help="Creator prefix")

    args = parser.parse_args()
    compile_mod(args.src, args.name, args.dist, args.creator)
