    # === NIGHT CONSERVATION ===
    # When sun is below threshold, nodes enter conservation:
    # - No movement cost (already handled if we skip movement)
    # - No BASE_COST (replaced by lower conservation cost)
    # - Reduced draw from stored

    for i in alive_idx:
        se = sun_intensity(t, pos[i])

        if se < 0.1:  # Night / low light
            # Conservation mode: only pay survival cost if stored > 0
            if stored[i] > 0:
                stored[i] -= 0.2  # Minimal survival draw
                trace_write('stored', stored[i], 'conserv:night_draw')
            else:
                energy[i] -= 0.1  # Bare minimum from main reserves
                trace_write('energy', energy[i], 'conserv:night_energy')
        else:
            # Daytime: normal metabolism already handled above
            pass