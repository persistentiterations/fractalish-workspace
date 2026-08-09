        trace_read('pressure', pressure[i], 'pressure:update_in')
        trace_read('bonds', len(bonds[i]), 'pressure:bond_count')
        pressure[i] = (pressure[i] + 2.0) * 0.85 + len(bonds[i]) * 0.2
        trace_write('pressure', pressure[i], 'pressure:update_out')