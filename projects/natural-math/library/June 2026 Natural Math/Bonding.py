            trace_read('energy', energy[i], 'bond:equalize_src')
            trace_read('energy', energy[j], 'bond:equalize_src')
            avg_e = 0.5 * (energy[i] + energy[j])
            energy[i] = avg_e
            energy[j] = avg_e
            trace_write('energy', energy[i], 'bond:equalize_dst')