# AGENT SPEC-DRIVEN CONTRACT: Simocoin Remote Mining Network (Headless)

**Target Ecosystem:** *The Sims 4* Engine (CPython 3.7.9 / Maxis Script VM)  
**Tuning Repository Reference:** `armoniapush/sims4-scripts-data` & Official EP17 (Businesses & Hobbies)  
**Parent Monorepo:** `ts4-mod-forge`  
**Target Mod Directory:** `mods/simocoin_network/scripts/simocoin_network/`  
**Deliverable Artifact:** `dist/TurboDrive_simocoin_network.ts4script`  
**Execution Profile:** Autonomous Software Engineering Agent (Cursor / Claude Code / Devin / Aider)

---

## 1. AGENT DIRECTIVES & HARD INVARIANTS

### 1.1 Non-Negotiable Directives
- **INV-01 (Strict Python 3.7.9 Syntax):** The codebase MUST be 100% syntactically valid under Python 3.7.9 (`magic number 3394` / `42 0D 0D 0A`). DO NOT use Python 3.8+ features: NO walrus operator (`:=`), NO positional-only parameters (`/`), NO `typing.Literal`, NO union operators (`|`).
- **INV-02 (Zero UI / 100% Headless):** Prohibido añadir diálogos, notificaciones emergentes, menús radiales (Pie Menu) o tablas de texto STBL. El mod es un subsistema invisible de fondo.
- **INV-03 (Cero Dependencias Externas):** Prohibido depender de *XML Injector*, *Lot 51 Core Library* u otras librerías intermedias. Usar exclusivamente la API estándar de Python y los módulos nativos de Maxis (`services`, `interactions`, `objects`, `sims4`).
- **INV-04 (Fidelidad Absoluta a la Simulación de Maxis):** NO alterar valores de dividendos, tablas de botín (LootActions), consumo de energía o duraciones. La replicación se realiza activando el `ObjectStateValue` nativo en cada computadora esclava.
- **INV-05 (Cerrojo Atómico de Reentrancia):** El interceptor de interacción DEBE implementar un cerrojo booleano (`_IS_REPLICATING`) para evitar bucles infinitos de microsegundos cuando las computadoras esclavas inicien sus procesos.
- **INV-06 (Topología de Empaquetado zipimport):** La raíz del archivo ZIP (`.ts4script`) debe contener directamente la carpeta del paquete `simocoin_network/`. Queda estrictamente prohibido prefijar con `scripts/` o rutas absolutas.
- **INV-07 (Fast-Path en Interacciones Globales):** Al enganchar `Interaction.on_run`, la función DEBE descartar en menos de 5 nanosegundos cualquier interacción que no sea una `SuperInteraction` (`not self.is_super`) o cuyo objetivo no sea un ordenador (`not getattr(self.target, 'is_computer', False)`), eliminando el 99.9% de sobrecoste de CPU en el juego.
- **INV-08 (Transacciones Financieras Atómicas):** La deducción de fondos debe utilizar `household.funds.try_remove(amount, reason, sim)` para garantizar consistencia atómica, compatibilidad con mods bancarios (SNB Bank) y prevención de saldo negativo sin comprobaciones manuales redundantes.

---

## 2. ARQUITECTURA DE ARCHIVOS Y RESPONSABILIDADES

Estructura de archivos bajo `mods/simocoin_network/scripts/`:

```
mods/simocoin_network/scripts/simocoin_network/
├── __init__.py                # Inicialización del paquete, banner de depuración y enganche de módulos
├── core/
│   ├── __init__.py            # Marcador de paquete core (archivo obligatorio)
│   └── injector.py            # Motor de inyección de métodos con preservación de metadatos (@wraps)
└── mining/
    ├── __init__.py            # Marcador de paquete mining (archivo obligatorio)
    ├── config.py              # Parámetros oficiales de Maxis, aranceles y constantes de telemetría
    ├── lot_scanner.py         # Escaneo O(N), saneamiento de hardware y jerarquía de seguridad de Maxis
    └── network_manager.py     # Orquestador con Fast-Path, memoización O(1), cerrojo y try_remove atómico
```

---

## 3. ESPECIFICACIÓN DETALLADA DE COMPONENTES (CÓDIGO CANÓNICO)

### 3.1 Módulo: `simocoin_network/core/__init__.py`

```python
# -*- coding: utf-8 -*-
# Core package marker
```

---

### 3.2 Módulo: `simocoin_network/core/injector.py`

#### Propósito
Inyección no destructiva en funciones y métodos del motor de Maxis en tiempo de ejecución.

#### Implementación Canónica
```python
# -*- coding: utf-8 -*-
import functools

def inject(target_object, target_function_name):
    """
    Decorador para inyección en tiempo de ejecución de Maxis.
    Preserva metadatos originales (__name__, __doc__, __module__).
    """
    def _wrap(new_function):
        if hasattr(target_object, target_function_name):
            original_function = getattr(target_object, target_function_name)

            @functools.wraps(original_function)
            def _injected(*args, **kwargs):
                return new_function(original_function, *args, **kwargs)

            setattr(target_object, target_function_name, _injected)
        return new_function
    return _wrap
```

---

### 3.3 Módulo: `simocoin_network/mining/__init__.py`

```python
# -*- coding: utf-8 -*-
# Mining package marker
```

---

### 3.4 Módulo: `simocoin_network/mining/config.py`

#### Propósito
Almacenar valores numéricos fijos, identificadores de telemetría y patrones de reconocimiento de la interacción de Simocoin de la expansión *Negocios y Hobbies*.

#### Implementación Canónica
```python
# -*- coding: utf-8 -*-

# Costo oficial de Maxis por cada sesión de minado de Simocoin
SIMOCOIN_ENTRY_COST = 100

# Palabras clave para identificación dinámica de la affordance en tiempo de ejecución
MINING_AFFORDANCE_KEYWORDS = ('simocoin', 'mine')

# Razón de telemetría oficial para la transacción bancaria de fondos
TELEMETRY_MONEY_REASON = 0
```

---

### 3.5 Módulo: `simocoin_network/mining/lot_scanner.py`

#### Propósito
Escanear el solar activo mediante `services.object_manager()`, realizar saneamiento de hardware (excluyendo objetos en destrucción, laptops cerradas, máquinas rotas y en uso) e implementar la jerarquía de seguridad nativa de Maxis (`OBJECT_LOCKING_COMPONENT`).

#### Implementación Canónica
```python
# -*- coding: utf-8 -*-
import services
from objects.components.types import STATE_COMPONENT, OBJECT_LOCKING_COMPONENT

def has_active_lock(lock_comp):
    """
    Duck-typing resiliente para detectar si la computadora tiene un candado
    activo de seguridad de Maxis, compatible con todas las versiones del juego.
    """
    if hasattr(lock_comp, 'has_lock'):
        try:
            return bool(lock_comp.has_lock()) if callable(lock_comp.has_lock) else bool(lock_comp.has_lock)
        except Exception:
            pass

    if hasattr(lock_comp, 'lock_type'):
        lt = lock_comp.lock_type
        if lt is not None and str(lt).lower() not in ('none', 'inactive', '0'):
            return True

    if hasattr(lock_comp, 'get_lock_type'):
        try:
            lt = lock_comp.get_lock_type()
            if lt is not None and str(lt).lower() not in ('none', 'inactive', '0'):
                return True
        except Exception:
            pass

    return False

def is_computer_locked_for_sim_exclusively(computer, sim):
    """
    Comprueba si la computadora tiene la seguridad nativa de Maxis configurada
    exclusivamente a nombre de este Sim (Bloquear para todos excepto este Sim).
    """
    if not computer.has_component(OBJECT_LOCKING_COMPONENT):
        return False

    lock_component = computer.get_component(OBJECT_LOCKING_COMPONENT)
    if lock_component is None or not has_active_lock(lock_component):
        return False

    if hasattr(lock_component, 'test_lock'):
        try:
            is_locked_out = bool(lock_component.test_lock(sim))
            return not is_locked_out
        except Exception:
            pass

    return False

def can_sim_access_computer(computer, sim):
    """
    Verifica si el Sim tiene autorización general para usar la computadora.
    """
    if hasattr(computer, 'can_sim_use'):
        try:
            return bool(computer.can_sim_use(sim))
        except Exception:
            pass

    if computer.has_component(OBJECT_LOCKING_COMPONENT):
        lock_comp = computer.get_component(OBJECT_LOCKING_COMPONENT)
        if lock_comp is not None and hasattr(lock_comp, 'test_lock'):
            try:
                return not bool(lock_comp.test_lock(sim))
            except Exception:
                pass

    return True

def get_target_mining_computers_gen(primary_computer_id, sim):
    """
    Generador de evaluación en dos niveles O(N) con descarte inmediato:
    - Nivel 1 (Granja Designada): Si el Sim tiene computadoras bloqueadas exclusivamente
      a su nombre, cede ÚNICAMENTE esas máquinas.
    - Nivel 2 (Granja Abierta / Fallback): Si el Sim no tiene ninguna computadora bloqueada
      para él, cede todas las computadoras libres, energizadas y desocupadas accesibles.
    """
    obj_manager = services.object_manager()
    if obj_manager is None:
        return

    designated_pcs = []
    available_open_pcs = []

    for obj in obj_manager.get_all():
        # Descarte ultrarrápido de Sims y máquina maestra
        if obj.id == primary_computer_id or getattr(obj, 'is_sim', False):
            continue

        # Descarte de objetos en proceso de destrucción por el motor
        if getattr(obj, 'is_ready_to_be_destroyed', False):
            continue

        # Descarte de objetos que no sean computadoras
        if not getattr(obj, 'is_computer', False):
            continue

        # Validar colocación física en el solar activo (excluye inventarios)
        if not obj.is_on_active_lot():
            continue

        # Saneamiento de hardware: averías, uso actual o laptops cerradas
        if getattr(obj, 'is_broken', False):
            continue
        if getattr(obj, 'in_use', False) or len(obj.get_users()) > 0:
            continue
        if getattr(obj, 'is_closed', False):
            continue

        # Debe poseer componente de estado para minar
        if not obj.has_component(STATE_COMPONENT):
            continue

        # Evaluación de seguridad y candados nativos
        if is_computer_locked_for_sim_exclusively(obj, sim):
            designated_pcs.append(obj)
        elif can_sim_access_computer(obj, sim):
            available_open_pcs.append(obj)

    targets = designated_pcs if designated_pcs else available_open_pcs
    for pc in targets:
        yield pc
```

---

### 3.6 Módulo: `simocoin_network/mining/network_manager.py`

#### Propósito
Interceptar `Interaction.on_run` mediante un filtro *Fast-Path* de descarte inmediato, extraer y memoizar el `ObjectStateValue` de minado nativo en $O(1)$, auditar y deducir fondos de forma atómica con `try_remove`, y propagar la activación.

#### Implementación Canónica
```python
# -*- coding: utf-8 -*-
import services
from interactions.base.interaction import Interaction
from simocoin_network.core.injector import inject
from simocoin_network.mining.config import (
    SIMOCOIN_ENTRY_COST,
    MINING_AFFORDANCE_KEYWORDS,
    TELEMETRY_MONEY_REASON
)
from simocoin_network.mining.lot_scanner import get_target_mining_computers_gen

# Cerrojo de reentrancia atómico
_IS_REPLICATING = False

# Caché memoizada del ObjectStateValue de minado para latencia O(1) tras el primer arranque
_CACHED_MINING_STATE_VALUE = None

def is_simocoin_mining_affordance(affordance):
    """
    Comprueba si una affordance corresponde a la interacción de minar Simocoin.
    """
    if affordance is None:
        return False
    aff_name = getattr(affordance, '__name__', '').lower()
    for kw in MINING_AFFORDANCE_KEYWORDS:
        if kw not in aff_name:
            return False
    return True

def extract_mining_state_value(primary_computer, interaction):
    """
    Resuelve deterministamente el ObjectStateValue de minería con memoización O(1).
    Estrategia 1: Caché de sesiones previas en memoria.
    Estrategia 2: Inspección estática de basic_extras en la affordance (latencia 0).
    Estrategia 3: Inspección dinámica de los estados activos del ordenador primario.
    """
    global _CACHED_MINING_STATE_VALUE
    if _CACHED_MINING_STATE_VALUE is not None:
        return _CACHED_MINING_STATE_VALUE

    # Estrategia 2: basic_extras de la definición de affordance
    affordance = getattr(interaction, 'affordance', None)
    if affordance is not None and hasattr(affordance, 'basic_extras'):
        for extra in affordance.basic_extras:
            state_values = getattr(extra, 'state_value_list', None)
            if state_values:
                for sv in state_values:
                    sv_str = str(sv).lower()
                    if 'mine' in sv_str or 'simocoin' in sv_str or 'crypto' in sv_str:
                        _CACHED_MINING_STATE_VALUE = sv
                        return sv

    # Estrategia 3: state_component del ordenador primario
    state_comp = getattr(primary_computer, 'state_component', None)
    if state_comp is not None and hasattr(state_comp, '_states'):
        for state_def, state_val in state_comp._states.items():
            val_str = str(state_val).lower()
            if 'simocoin' in val_str or 'mining' in val_str:
                _CACHED_MINING_STATE_VALUE = state_val
                return state_val

    return None

def replicate_mining_network(primary_interaction):
    """
    Orquesta la propagación remota del proceso de minería a las computadoras esclavas.
    """
    global _IS_REPLICATING
    if _IS_REPLICATING:
        return

    primary_computer = primary_interaction.target
    sim = primary_interaction.sim

    if primary_computer is None or sim is None:
        return

    household = getattr(sim, 'household', None)
    if household is None or not hasattr(household, 'funds'):
        return

    _IS_REPLICATING = True
    try:
        mining_state_value = extract_mining_state_value(primary_computer, primary_interaction)
        if mining_state_value is None:
            return

        funds = household.funds

        for slave_pc in get_target_mining_computers_gen(primary_computer.id, sim):
            # Evitar encender una computadora que ya esté minando
            if slave_pc.get_state(mining_state_value.state) == mining_state_value:
                continue

            # Transacción atómica compatible con SNB Bank / FundsTracker
            if hasattr(funds, 'try_remove'):
                if not funds.try_remove(SIMOCOIN_ENTRY_COST, TELEMETRY_MONEY_REASON, sim):
                    break
            else:
                if funds.money < SIMOCOIN_ENTRY_COST:
                    break
                funds.remove(SIMOCOIN_ENTRY_COST, TELEMETRY_MONEY_REASON)

            # Encender proceso y temporizador nativo de Maxis en la máquina esclava
            slave_pc.set_state(mining_state_value.state, mining_state_value)

    finally:
        _IS_REPLICATING = False

@inject(Interaction, 'on_run')
def _hook_on_interaction_run(original, self, *args, **kwargs):
    """
    Intercepta el inicio de cualquier interacción.
    Fast-Path: el 99.9% de interacciones en el juego se descartan en <5 nanosegundos
    sin comprobaciones de cadenas de texto ni accesos de memoria pesados.
    """
    result = original(self, *args, **kwargs)
    if result is False:
        return result

    # Filtro 1: Descartar interacciones que no sean SuperInteractions
    if not getattr(self, 'is_super', False):
        return result

    # Filtro 2: Descartar interacciones cuyo target no sea una computadora (caminar, comer, etc.)
    target = getattr(self, 'target', None)
    if target is None or not getattr(target, 'is_computer', False):
        return result

    # Solo si el usuario ejecutó una SuperInteracción sobre un ordenador, validamos Simocoin
    try:
        if is_simocoin_mining_affordance(self.affordance):
            replicate_mining_network(self)
    except Exception:
        pass

    return result
```

---

### 3.7 Módulo: `simocoin_network/__init__.py`

#### Propósito
Punto de entrada del paquete. Al ser cargado por el motor de Maxis, inicializa el módulo `network_manager` para registrar los hooks en memoria.

#### Implementación Canónica
```python
# -*- coding: utf-8 -*-
"""
TurboDrive Simocoin Network Mod
Automated Headless Rig Replicator for The Sims 4: Businesses & Hobbies
"""
from simocoin_network.mining import network_manager
```

---

## 4. PROTOCOLO DE COMPILACIÓN Y EMPAQUETADO

### 4.1 Comando de Compilación (desde la raíz de `ts4-mod-forge`)
```powershell
.\.conda-env\python.exe tools\compiler\compiler.py --src "mods\simocoin_network\scripts" --name "simocoin_network" --creator "TurboDrive" --dist "dist"
```

### 4.2 Verificación Estricta del Contenedor ZIP (`.ts4script`)
El agente debe verificar programáticamente que la estructura interna de `dist/TurboDrive_simocoin_network.ts4script` cumpla con la regla de raíz de `zipimport`:

```
TurboDrive_simocoin_network.ts4script
├── simocoin_network/
│   ├── __init__.pyc
│   ├── core/
│   │   ├── __init__.pyc
│   │   └── injector.pyc
│   └── mining/
│       ├── __init__.pyc
│       ├── config.pyc
│       ├── lot_scanner.pyc
│       └── network_manager.pyc
```

---

## 5. MATRIZ DE VERIFICACIÓN Y PRUEBAS FALSABLES

| ID | Condición de Prueba | Acción Ejecutada | Aserción Falsable |
|---|---|---|---|
| **TEST-01** | Magic Number CPython 3.7 | Leer primeros 4 bytes de cada `.pyc` compilado | Los bytes son exactamente `b'\x42\r\r\n'` (decimal 3394). |
| **TEST-02** | Sintaxis Python 3.7 | Compilar con `py_compile` en Python 3.7.9 | Cero errores de sintaxis; sin operadores `:=` ni `/`. |
| **TEST-03** | Aborto en Falla Primaria | El Sim no puede enrutar hacia la computadora maestra (`result is False`) | Cero computadoras esclavas son encendidas; §0 deducidos. |
| **TEST-04** | Aislamiento de Granja Designada | 4 PCs bloqueadas a Sim A, 1 PC bloqueada a Sim B. Sim A inicia minado. | Se activan las 4 de Sim A y la maestra (§500 deducidos). La PC de Sim B permanece intacta. |
| **TEST-05** | Fallback a Granja Abierta | Cero PCs con candados. 6 PCs desocupadas en el solar. | Se activan las 6 PCs si los fondos alcanzan (§700 deducidos en total). |
| **TEST-06** | Límite Contable Estricto | Fondos = §250. 5 PCs desocupadas. Sim A inicia minado. | Maestra descuenta §100 (saldo §150). Solo 1 esclava descuenta §100 (saldo §50). Las restantes 4 quedan apagadas. |
| **TEST-07** | Tolerancia a Laptops Cerradas y Averías | 1 PC rota y 1 laptop cerrada en la mesa. | Ambas son ignoradas por el escáner sin producir excepciones. |
| **TEST-08** | Inmunidad de Reentrancia | 20 computadoras en red. | `_IS_REPLICATING` previene llamadas recursivas; tiempo total de ejecución del hook < 2 ms. |
| **TEST-09** | Cero Side-Effects en Interacciones Ajenas | El Sim cocina, duerme, habla o navega por la web. | `is_simocoin_mining_affordance` no se evalúa; el Fast-Path descarta en <5 ns; cero llamadas al escáner. |
| **TEST-10** | Compatibilidad SNB / try_remove | Sim realiza transacción con mod bancario instalado. | Deducción atómica registrada con telemetry reason y referencia a `sim`. |
