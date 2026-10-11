# -*- coding: utf-8 -*-
import zone
from simocoin_network.core.injector import inject
from simocoin_network.mining import network_manager

def _boot_log(msg):
    try:
        with open('C:\\Users\\armon\\Documents\\Electronic Arts\\Los Sims 4\\hashstratum_debug.log', 'a', encoding='utf-8') as lf:
            lf.write('[HashStratum Boot] ' + str(msg) + '\n')
    except Exception:
        pass

_boot_log('simocoin_network __init__.py executed upon module load!')

@inject(zone.Zone, 'on_loading_screen_animation_finished')
def _on_zone_loaded(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    _boot_log('Zone loaded! HashStratum hooks verified and active.')
    return result
