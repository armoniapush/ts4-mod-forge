# TS4 Mod Forge

Monorepo y entorno de desarrollo modular para crear, compilar y empaquetar mods de código (`.ts4script`) y tuning para **The Sims 4**.

---

## 🎯 Objetivo del Proyecto

El motor de Los Sims 4 corre internamente sobre una versión modificada de Python cuyo cliente de Maxis **requiere de forma obligatoria bytecode de Python 3.7** (`magic number 3394`). Si los scripts se compilan con Python >= 3.8, el juego no puede leer los archivos `.pyc` dentro del archivo `.ts4script` y el mod no se carga.

**TS4 Mod Forge** centraliza:
- Un entorno de ejecución local aislado anclado a **Python 3.7.9**.
- Arquitectura modular donde cada mod desarrollado reside en `mods/` (como submódulo Git o paquete independiente).
- Pipeline de compilación y empaquetado automático de `.py` a `.ts4script`.
- Herramientas auxiliares para descompilación de los scripts nativos de Maxis, inyección (XML Injector, Lot 51) y tuning DBPF.

---

## 📁 Estructura del Espacio de Trabajo

```
ts4-mod-forge/
├── .conda-env/             # Entorno local aislado con Python 3.7.9 (ignorado por Git)
├── mods/                   # Submódulos y proyectos individuales de mods
│   └── <tu_mod>/
│       └── scripts/        # Código fuente Python (.py)
├── shared/                 # Código compartido, stubs y tipos de la API de TS4
├── tools/
│   ├── compiler/           # Pipeline de compilación de bytecode y empaquetado zip
│   │   └── compiler.py     # Script que fuerza la compilación en Python 3.7
│   ├── templates/          # Plantillas de referencia (Sims4ScriptingTemplate, etc.)
│   └── scripts/            # Automatizaciones y tareas de despliegue
├── dist/                   # Artefactos empaquetados listos para Mods/ de TS4
├── pyproject.toml          # Configuración del proyecto base
└── README.md
```

---

## ⚙️ Requisitos y Configuración Rápida

### 1. Entorno de Ejecución
El proyecto incluye un entorno aislado con Python 3.7.9 configurado en `.conda-env`. Para verificarlo:

```powershell
.\.conda-env\python.exe --version
# Salida esperada: Python 3.7.9
```

### 2. Compilar y Empaquetar un Mod
Para compilar un mod a formato `.ts4script` garantizando compatibilidad total con el bytecode del juego:

```powershell
.\.conda-env\python.exe tools\compiler\compiler.py --src "mods\<nombre_mod>\scripts" --name "<nombre_mod>" --creator "<tu_alias>" --dist "dist"
```

El script genera automáticamente el archivo empaquetado en:
`dist/<tu_alias>_<nombre_mod>.ts4script`

---

## 🛠️ Herramientas y Ecosistema de Referencia

- **Intérprete**: Python 3.7.9 (CPython Windows x64).
- **Hooks & Inyección**: Compatible con [Lot 51 Core Library](https://github.com/lot51/core-library) y [XML Injector](https://scumbumbomods.com/xml-injector).
- **Descompilación**: Plantilla base integrada en `tools/templates/mycroftjr` para extraer y analizar los scripts originales de Maxis.
- **Tuning de Datos**: Soporte para empaquetado en archivos `.package` vía Sims 4 Studio.
