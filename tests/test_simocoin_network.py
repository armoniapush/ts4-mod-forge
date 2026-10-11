import sys
import unittest
from unittest.mock import MagicMock

# Mock Maxis modules before imports
services_mock = MagicMock()
interactions_mock = MagicMock()
objects_components_types_mock = MagicMock()

sys.modules['services'] = services_mock
sys.modules['interactions'] = interactions_mock
sys.modules['interactions.base'] = MagicMock()
sys.modules['interactions.base.interaction'] = interactions_mock
sys.modules['objects'] = MagicMock()
sys.modules['objects.components'] = MagicMock()
sys.modules['objects.components.types'] = objects_components_types_mock

STATE_COMPONENT = "STATE_COMPONENT"
OBJECT_LOCKING_COMPONENT = "OBJECT_LOCKING_COMPONENT"
objects_components_types_mock.STATE_COMPONENT = STATE_COMPONENT
objects_components_types_mock.OBJECT_LOCKING_COMPONENT = OBJECT_LOCKING_COMPONENT

class Interaction:
    is_super = True
    def on_run(self, *args, **kwargs):
        return True

interactions_mock.Interaction = Interaction

sys.path.insert(0, r"mods\simocoin_network\scripts")

import simocoin_network.core.injector as injector
import simocoin_network.mining.config as config
import simocoin_network.mining.lot_scanner as lot_scanner
import simocoin_network.mining.network_manager as network_manager

class TestSimocoinNetwork(unittest.TestCase):
    def setUp(self):
        network_manager._IS_REPLICATING = False
        network_manager._CACHED_MINING_STATE_VALUE = None

    def test_test03_abort_on_primary_failure(self):
        """TEST-03: Aborto en falla primaria (result is False)."""
        instance = Interaction()
        original = MagicMock(return_value=False)
        res = network_manager._hook_on_interaction_run(original, instance)
        self.assertFalse(res)
        self.assertFalse(network_manager._IS_REPLICATING)

    def test_test07_hardware_sanitization(self):
        """TEST-07: Tolerancia a laptops cerradas, averias, en uso y no-lote."""
        sim = MagicMock()
        primary_pc = MagicMock(id=1, is_sim=False, is_ready_to_be_destroyed=False, is_computer=True)
        broken_pc = MagicMock(id=2, is_sim=False, is_ready_to_be_destroyed=False, is_computer=True, is_on_active_lot=MagicMock(return_value=True), is_broken=True)
        closed_laptop = MagicMock(id=3, is_sim=False, is_ready_to_be_destroyed=False, is_computer=True, is_on_active_lot=MagicMock(return_value=True), is_broken=False, is_closed=True)
        in_use_pc = MagicMock(id=4, is_sim=False, is_ready_to_be_destroyed=False, is_computer=True, is_on_active_lot=MagicMock(return_value=True), is_broken=False, is_closed=False, in_use=True)
        good_pc = MagicMock(id=5, is_sim=False, is_ready_to_be_destroyed=False, is_computer=True, is_on_active_lot=MagicMock(return_value=True), is_broken=False, is_closed=False, in_use=False, get_users=MagicMock(return_value=[]), has_component=MagicMock(return_value=True))
        good_pc.has_component.side_effect = lambda comp: comp == STATE_COMPONENT

        services_mock.object_manager.return_value.get_all.return_value = [
            primary_pc, broken_pc, closed_laptop, in_use_pc, good_pc
        ]

        targets = list(lot_scanner.get_target_mining_computers_gen(1, sim))
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].id, 5)

    def test_test04_designated_farm_isolation(self):
        """TEST-04: Aislamiento de granja designada con candados exclusivos."""
        sim_a = MagicMock()
        sim_b = MagicMock()

        def make_pc(pid, locked_to_sim):
            pc = MagicMock(id=pid, is_sim=False, is_ready_to_be_destroyed=False, is_computer=True,
                           is_on_active_lot=MagicMock(return_value=True), is_broken=False, is_closed=False,
                           in_use=False, get_users=MagicMock(return_value=[]))
            lock_comp = MagicMock()
            lock_comp.has_lock = True
            lock_comp.test_lock.side_effect = lambda s: False if s == locked_to_sim else True
            pc.get_component.return_value = lock_comp
            pc.has_component.side_effect = lambda comp: True
            return pc

        pcs = [make_pc(10 + i, sim_a) for i in range(4)]
        pcs.append(make_pc(20, sim_b))

        services_mock.object_manager.return_value.get_all.return_value = pcs
        targets = list(lot_scanner.get_target_mining_computers_gen(1, sim_a))
        self.assertEqual(len(targets), 4)
        target_ids = [p.id for p in targets]
        self.assertEqual(target_ids, [10, 11, 12, 13])

    def test_test06_strict_financial_limit(self):
        """TEST-06: Limite contable estricto y atomicidad try_remove."""
        state_val = MagicMock()
        state_val.state = "SIMOCOIN_STATE"
        network_manager._CACHED_MINING_STATE_VALUE = state_val

        sim = MagicMock()
        household = MagicMock()
        sim.household = household
        funds = MagicMock()
        household.funds = funds
        funds.try_remove.side_effect = [True, False]  # Solo fondos para 1 esclava

        pcs = []
        for i in range(5):
            pc = MagicMock(id=100 + i)
            pc.get_state.return_value = "OFF"
            pcs.append(pc)

        with unittest.mock.patch('simocoin_network.mining.network_manager.get_target_mining_computers_gen', return_value=iter(pcs)):
            interaction = MagicMock()
            interaction.target = MagicMock(id=99)
            interaction.sim = sim
            network_manager.replicate_mining_network(interaction)

        # Solo la primera debe haber recibido set_state
        pcs[0].set_state.assert_called_once_with("SIMOCOIN_STATE", state_val)
        pcs[1].set_state.assert_not_called()
        self.assertEqual(funds.try_remove.call_count, 2)

    def test_test08_reentrancy_lock(self):
        """TEST-08: Inmunidad de reentrancia."""
        network_manager._IS_REPLICATING = True
        interaction = MagicMock()
        network_manager.replicate_mining_network(interaction)
        interaction.sim.household.funds.try_remove.assert_not_called()

    def test_test09_fast_path_discard(self):
        """TEST-09: Descarte inmediato de interacciones no-super o no-computadora."""
        original = MagicMock(return_value=True)

        # Caso 1: not is_super
        it1 = MagicMock(is_super=False)
        res1 = network_manager._hook_on_interaction_run(original, it1)
        self.assertTrue(res1)

        # Caso 2: target no es computer
        it2 = MagicMock(is_super=True, target=MagicMock(is_computer=False))
        res2 = network_manager._hook_on_interaction_run(original, it2)
        self.assertTrue(res2)

if __name__ == '__main__':
    unittest.main()
