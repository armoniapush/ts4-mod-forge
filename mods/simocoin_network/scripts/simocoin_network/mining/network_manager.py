# -*- coding: utf-8 -*-
import alarms
import clock
import services
from interactions.base.interaction import Interaction
from interactions.interaction_queue import InteractionQueue
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

def _execute_replicate_mining(primary_computer_id, sim_id, interaction_ref):
    global _IS_REPLICATING
    if _IS_REPLICATING:
        return

    _IS_REPLICATING = True
    try:
        obj_manager = services.object_manager()
        if obj_manager is None:
            return

        primary_computer = obj_manager.get(primary_computer_id)
        sim = obj_manager.get(sim_id)
        if primary_computer is None or sim is None:
            return

        household = getattr(sim, 'household', None)
        if household is None or not hasattr(household, 'funds'):
            return

        _log_debug('[_execute_replicate_mining] Starting replication. Master PC: ' + str(primary_computer_id) + ', Sim: ' + str(sim))
        mining_state_value = extract_mining_state_value(primary_computer, interaction_ref)
        _log_debug('Resolved mining_state_value: ' + str(mining_state_value))
        
        comp = get_simocoin_farming_component(primary_computer)
        farming_stat = getattr(comp, 'farming_stat', None) if comp is not None else None
        _log_debug('Resolved farming_stat: ' + str(farming_stat))

        funds = household.funds
        activated_count = 0

        for slave_pc in get_target_mining_computers_gen(primary_computer.id, sim):
            _log_debug('Evaluating slave PC ID: ' + str(slave_pc.id))
            if mining_state_value is not None:
                if slave_pc.get_state(mining_state_value.state) == mining_state_value:
                    _log_debug('Slave PC already in state: ' + str(slave_pc.id))
                    continue

            if hasattr(funds, 'try_remove'):
                if not funds.try_remove(SIMOCOIN_ENTRY_COST, TELEMETRY_MONEY_REASON, sim):
                    _log_debug('try_remove failed (insufficient funds). Aborting remaining.')
                    break
            else:
                if funds.money < SIMOCOIN_ENTRY_COST:
                    _log_debug('Insufficient funds. Aborting remaining.')
                    break
                funds.remove(SIMOCOIN_ENTRY_COST, TELEMETRY_MONEY_REASON)

            if mining_state_value is not None:
                try:
                    slave_pc.set_state(mining_state_value.state, mining_state_value, immediate=True, force_update=True)
                except TypeError:
                    slave_pc.set_state(mining_state_value.state, mining_state_value)
                _log_debug('set_state applied to slave PC ID: ' + str(slave_pc.id))

            if farming_stat is not None:
                slave_stat_comp = getattr(slave_pc, 'statistic_component', None)
                if slave_stat_comp is not None:
                    tracker = slave_stat_comp.get_commodity_tracker()
                    if tracker is not None:
                        stat_inst = tracker.add_statistic(farming_stat)
                        if stat_inst is not None:
                            stat_inst.set_value(stat_inst.max_value)
                            _log_debug('Set commodity tracker max value on slave PC ID: ' + str(slave_pc.id))

            slave_farming_comp = get_simocoin_farming_component(slave_pc)
            if slave_farming_comp is not None and hasattr(slave_farming_comp, '_refresh'):
                slave_farming_comp._refresh()
                _log_debug('_refresh called on slave farming component ID: ' + str(slave_pc.id))

            activated_count += 1

        _log_debug('<<< Replication complete. Total slave computers activated: ' + str(activated_count))

    except Exception as e:
        _log_debug('Exception in _execute_replicate_mining: ' + str(e))
    finally:
        _IS_REPLICATING = False

def schedule_delayed_replication(primary_interaction):
    primary_computer = getattr(primary_interaction, 'target', None)
    sim = getattr(primary_interaction, 'sim', None)
    if primary_computer is None or sim is None:
        return

    primary_computer_id = primary_computer.id
    sim_id = sim.id

    def _alarm_callback(timeline):
        _execute_replicate_mining(primary_computer_id, sim_id, primary_interaction)

    time_delay = clock.interval_in_sim_seconds(1)
    alarms.add_alarm(primary_interaction, time_delay, _alarm_callback)
    _log_debug('Alarm scheduled for delayed replication (1 sim sec) on PC ID: ' + str(primary_computer_id))

def _process_potential_mining_interaction(interaction):
    if interaction is None:
        return
    if not getattr(interaction, 'is_super', False):
        return

    target = getattr(interaction, 'target', None)
    if target is None or not getattr(target, 'is_computer', False):
        return

    try:
        aff = getattr(interaction, 'affordance', None)
        aff_name = getattr(aff, '__name__', '')
        _log_debug('Intercepted computer SuperInteraction: ' + str(aff_name) + ', target ID: ' + str(getattr(target, 'id', None)))
        if is_simocoin_mining_context(target, aff):
            _log_debug('>>> Matched Simocoin context! Scheduling delayed batch replication...')
            schedule_delayed_replication(interaction)
    except Exception as e:
        _log_debug('Error in _process_potential_mining_interaction: ' + str(e))

@inject(InteractionQueue, 'run_interaction_gen')
def _hook_on_interaction_queue_run(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        if result and len(args) > 1:
            interaction = args[1]
            _process_potential_mining_interaction(interaction)
    except Exception as e:
        _log_debug('Error in InteractionQueue hook: ' + str(e))
    return result

@inject(Interaction, 'on_run')
def _hook_on_interaction_run(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    if result is False:
        return result
    try:
        _process_potential_mining_interaction(self)
    except Exception as e:
        _log_debug('Error in Interaction.on_run fallback hook: ' + str(e))
    return result
