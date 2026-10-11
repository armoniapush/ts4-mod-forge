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
