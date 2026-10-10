---
name: ts4-headless-engine
description: >-
  Use this skill when developing, refactoring, or reviewing pure Python script mods (.ts4script) for The Sims 4.
  Provides technical guidelines on the headless simulation architecture, zero-UI operations, monkey patching,
  strict UI/Scaleform boundaries, and criteria for requiring DBPF .package tuning.
---

# TS4 Headless Engine & Script Architecture

## 1. Runtime Architecture

- **Two-Layer Engine**: The Sims 4 engine separates the simulation core (Python 3.7.x) from the graphics, physics, and UI layer (C++).
- **Synchronous In-Memory Execution**: `.ts4script` archives are loaded via `zipimport` into the simulation thread VM.
- **Headless Execution**: Mod scripts intercept data, mutate logic, monkey patch methods, and alter object state directly in memory without requiring C++ visual meshes, animations, or UI rendering passes.

## 2. Operational Logic & Headless Constraints

```
if task.requires_pure_logic_or_data:
    execute_in_memory_headless_hooks()
    assert no_package_file_needed()
    assert no_savegame_corruption_risk()
elif task.requires_ui_or_pie_menu:
    assert use_native_dialog_classes_only()
    if task.registers_new_tuning_or_strings:
        require_dbpf_package(tuning_xml=True, stbl=True)
```

### Advantages
- **Patch Immunity**: Zero coupling to visual layouts or Scaleform assets; resilient across visual game updates.
- **Optimized Execution (O(N))**: Heavy loops over lot objects, math, or state machines execute directly in microsecond VM operations.
- **Safe-Uninstall**: Operating on live memory variables leaves zero residual artifacts in `.save` files, avoiding zone load crashes upon removal.
- **Invisible Automation**: Direct state mutation bypasses Sim posture graphs and physical interaction queues.

## 3. Strict UI Boundaries (Scaleform & Protobuf)

- **Scaleform / Flash Limitation**: UI is compiled ActionScript (`.gfx`). Python cannot instantiate arbitrary UI widgets dynamically.
- **Allowed Native Dialogs**: Only native Maxis dialog classes can be invoked (e.g., `UiDialogOk`, `UiDialogOkCancel`, `UiDialogObjectPicker`).
- **Protobuf Communication**: UI triggers serialize structured 64-bit instance IDs to C++. Non-registered IDs or unmapped classes cause fatal desyncs (`AttributeError: type object has no attribute 'guid64'`).
- **No Hot-Reloading**: `importlib.reload()` cannot be used on modules interacting with UI descriptors while the game client runs.

## 4. DBPF Package Dependency Matrix

| Mod Requirement | `.ts4script` Only | Requires `.package` (DBPF) |
| :--- | :--- | :--- |
| Pure logic / automation / memory hooks | YES | NO |
| Dynamic state mutation / Simoleons | YES | NO |
| Pie menu interactions (SuperInteraction) | NO | YES (Instance Manager XML) |
| Localized strings / notifications | NO | YES (STBL tables) |
| Custom icons / meshes / textures | NO | YES (DBPF binary) |
| XML Injector snippet integration | NO | YES (Tuning resource) |
