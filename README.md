# TS4 Mod Forge

Modular development workspace & build pipeline for The Sims 4 script mods (`.ts4script`).

## Architecture & Layout

```
ts4-mod-forge/
├── mods/                 # Submodulos / mods independientes
├── shared/               # Librerías comunes y stubs de la API de TS4
├── tools/
│   ├── compiler/         # Compilador y empaquetador de bytecode Python 3.7
│   └── scripts/          # Automatizaciones auxiliares
├── dist/                 # Artefactos compilados listos para Mods/
├── pyproject.toml        # Gestión con uv
└── README.md
```

## Python 3.7.9 Requirement

The Sims 4 runtime requires bytecode compiled strictly with Python 3.7 (`magic number 3394`). Bytecode from Python >= 3.8 will fail to load in the client.
