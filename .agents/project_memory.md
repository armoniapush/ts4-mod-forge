# TS4 Mod Forge - Isometric Project Ledger

## Project Identity
- **Project**: `ts4-mod-forge`
- **Core Engine**: Pure Python 3.7.x headless simulation (Maxis client bytecode compatibility `magic number 3394`).
- **Workspace Model**: Modular Monorepo (`mods/` submodules, `tools/compiler/`, `shared/`, `dist/`).

## Immutable Technical Directives
1. **Python 3.7.9 Isolation**:
   - Environment path: `.conda-env\python.exe`.
   - Never compile with Python >= 3.8 (fails silently in game runtime).
2. **Zipimport Root Packaging**:
   - Root of `.ts4script` archive must be strictly `<mod_name>/` containing `__init__.pyc`.
   - Never embed `scripts/` or host directories in zip root.
3. **Folder Nesting Limit in Mods/**:
   - Maxis only resolves `.ts4script` up to 1 subfolder depth: `Mods/Folder/mod.ts4script` (valid), `Mods/Sub1/Sub2/mod.ts4script` (ignored).
4. **Headless Zero-Package Protocol**:
   - Pure runtime hooks & data mods require 0 `.package` DBPF files.
   - Only require `.package` when registering new XML Tuning instances (Pie Menu), STBL strings, or visual assets.

## Active Modules & Tools
- `tools/compiler/compiler.py`: Compiler forcing Python 3.7.9 bytecode and strict package root layout.
- `tools/templates/mycroftjr`: Cloned reference framework.
- `.agents/skills/ts4-headless-engine/SKILL.md`: Project-specific architectural skill.
