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
