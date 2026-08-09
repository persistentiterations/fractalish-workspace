        trace_read('energy', energy[i], 'metab:sun_in')
        energy[i] += se
        trace_write('energy', energy[i], 'metab:sun_post')