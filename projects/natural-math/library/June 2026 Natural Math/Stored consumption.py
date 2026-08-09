        trace_read('stored', stored[i], 'metab:use_stored')
        use = min(stored[i], 2.0)
        energy[i] += use
        stored[i] -= use
        trace_write('stored', stored[i], 'metab:stored_used')
        trace_write('energy', energy[i], 'metab:stored_to_energy')