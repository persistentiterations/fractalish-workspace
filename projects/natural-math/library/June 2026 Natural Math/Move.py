    for i in alive_idx:
        fn = np.linalg.norm(forces[i])
        if fn > 0.01 and energy[i] > 0.5: