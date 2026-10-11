# -*- coding: utf-8 -*-
import services
import sims4.log
from interactions.base.interaction import Interaction
from simocoin_network.core.injector import inject
from simocoin_network.mining.config import (
    SIMOCOIN_ENTRY_COST,
    TELEMETRY_MONEY_REASON
)
from simocoin_network.mining.lot_scanner import get_target_mining_computers_gen

try:
    from objects.components.types import SIMOCOIN_FARMING_COMPONENT
except ImportError:
    SIMOCOIN_FARMING_COMPONENT = None

def _log_debug(msg):
    try:
        with open('C:\\Users\\armon\\Documents\\Electronic Arts\\Los Sims 4\\hashstratum_debug.log', 'a', encoding='utf-8') as lf:
            lf.write(str(msg) + '\n')
    except Exception:
        pass

_IS_REPLICATING = False
_CACHED_MINING_STATE_VALUE = None

def get_simocoin_farming_component(obj):
    if SIMOCOIN_FARMING_COMPONENT is not None and hasattr(obj, 'get_component'):
        comp = obj.get_component(SIMOCOIN_FARMING_COMPONENT)
        if comp is not None:
            return comp
    if hasattr(obj, 'simocoin_farming_component'):
        return obj.simocoin_farming_component
    return None

def is_simocoin_mining_context(primary_computer, affordance):
    if affordance is not None:
        aff_name = getattr(affordance, '__name__', '').lower()
        class_name = getattr(affordance, '__class__', {}).__name__.lower() if hasattr(affordance, '__class__') else ''
        for kw in ('simocoin', 'mine', 'crypto', 'farming'):
            if kw in aff_name or kw in class_name:
                return True

    comp = get_simocoin_farming_component(primary_computer)
    if comp is not None:
        return True

    return False

def extract_mining_state_value(primary_computer, interaction):
    global _CACHED_MINING_STATE_VALUE
    if _CACHED_MINING_STATE_VALUE is not None:
        return _CACHED_MINING_STATE_VALUE

    comp = get_simocoin_farming_component(primary_computer)
    if comp is not None:
        sv = getattr(comp, 'farming_state_value', None)
        if sv is not None:
            _CACHED_MINING_STATE_VALUE = sv
            _log_debug('Found farming_state_value via SimoCoinFarmingComponent: ' + str(sv))
            return sv

    affordance = getattr(interaction, 'affordance', None)
    if affordance is not None and hasattr(affordance, 'basic_extras'):
        for extra in affordance.basic_extras:
            state_values = getattr(extra, 'state_value_list', None)
            if state_values:
                for sv in state_values:
                    sv_str = str(sv).lower()
                    if 'mine' in sv_str or 'simocoin' in sv_str or 'crypto' in sv_str or 'farm' in sv_str:
                        _CACHED_MINING_STATE_VALUE = sv
                        _log_debug('Found state value via basic_extras: ' + str(sv))
                        return sv

    state_comp = getattr(primary_computer, 'state_component', None)
    if state_comp is not None and hasattr(state_comp, '_states'):
        for state_def, state_val in state_comp._states.items():
            val_str = str(state_val).lower()
            if 'simocoin' in val_str or 'mining' in val_str or 'farm' in val_str:
                _CACHED_MINING_STATE_VALUE = state_val
                _log_debug('Found state value via state_comp._states: ' + str(state_val))
                return state_val

    return None

def replicate_mining_network(primary_interaction):
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
        _log_debug('replicate_mining_network starting on primary PC: ' + str(primary_computer))
        mining_state_value = extract_mining_state_value(primary_computer, primary_interaction)
        _log_debug('Resolved mining_state_value: ' + str(mining_state_value))
        
        comp = get_simocoin_farming_component(primary_computer)
        farming_stat = getattr(comp, 'farming_stat', None) if comp is not None else None
        _log_debug('Resolved farming_stat: ' + str(farming_stat))

        funds = household.funds

        for slave_pc in get_target_mining_computers_gen(primary_computer.id, sim):
            _log_debug('Evaluating slave PC: ' + str(slave_pc))
            if mining_state_value is not None:
                if slave_pc.get_state(mining_state_value.state) == mining_state_value:
                    _log_debug('Slave PC already in state: ' + str(slave_pc))
                    continue

            if hasattr(funds, 'try_remove'):
                if not funds.try_remove(SIMOCOIN_ENTRY_COST, TELEMETRY_MONEY_REASON, sim):
                    _log_debug('try_remove returned False. Stopping replication.')
                    break
            else:
                if funds.money < SIMOCOIN_ENTRY_COST:
                    _log_debug('Not enough funds. Stopping replication.')
                    break
                funds.remove(SIMOCOIN_ENTRY_COST, TELEMETRY_MONEY_REASON)

            if mining_state_value is not None:
                slave_pc.set_state(mining_state_value.state, mining_state_value)
                _log_debug('set_state applied to slave PC: ' + str(slave_pc))

            if farming_stat is not None:
                slave_stat_comp = getattr(slave_pc, 'statistic_component', None)
                if slave_stat_comp is not None:
                    tracker = slave_stat_comp.get_commodity_tracker()
                    if tracker is not None:
                        stat_inst = tracker.add_statistic(farming_stat)
                        if stat_inst is not None:
                            stat_inst.set_value(stat_inst.max_value)
                            _log_debug('Set commodity tracker stat value on slave PC')

            slave_farming_comp = get_simocoin_farming_component(slave_pc)
            if slave_farming_comp is not None and hasattr(slave_farming_comp, '_refresh'):
                slave_farming_comp._refresh()
                _log_debug('_refresh called on slave farming component')

    except Exception as e:
        _log_debug('Exception in replicate_mining_network: ' + str(e))
    finally:
        _IS_REPLICATING = False

@inject(Interaction, 'on_run')
def _hook_on_interaction_run(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    if result is False:
        return result

    if not getattr(self, 'is_super', False):
        return result

    target = getattr(self, 'target', None)
    if target is None or not getattr(target, 'is_computer', False):
        return result

    try:
        aff_name = getattr(self.affordance, '__name__', '')
        _log_debug('Computer SuperInteraction on_run: affordance=' + str(aff_name) + ', target=' + str(target))
        if is_simocoin_mining_context(target, self.affordance):
            _log_debug('Matched Simocoin context! Triggering replication...')
            replicate_mining_network(self)
    except Exception as e:
        _log_debug('Error in hook: ' + str(e))

    return result
