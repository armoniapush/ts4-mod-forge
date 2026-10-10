# Project Rules: TS4 Mod Forge

## Automatic Memory Recall
- At the start of every session, read `.agents/project_memory.md` to restore architectural constraints, package root rules, and environment paths.
- Before concluding major milestones, update `.agents/project_memory.md` with new modules, verified Maxis API patterns, or build changes.

## Environment Constraints
- Local Python 3.7.9 interpreter: `.conda-env\python.exe`.
- Compiler script: `tools\compiler\compiler.py`.
- No `.package` files unless explicit XML tuning / STBL localization is requested.
