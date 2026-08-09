        trace_read('energy', energy[i], 'bifurc:parent_pre_split')
        energy[i] *= 0.6
        trace_write('energy', energy[i], 'bifurc:parent_post_split')