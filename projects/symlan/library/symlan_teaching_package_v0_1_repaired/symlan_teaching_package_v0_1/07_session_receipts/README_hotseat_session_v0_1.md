# Hotseat session receipt export + local replay v0.1

Play a few turns on `hotseat_play_surface_v0_1.html`, click **Export session** to download a `symlan.hotseat_session.v0.1` JSON (initial PlayableState + hashed event list + final tip), then **Load session** (file or paste) to restore the board, slice S, turn, receipts tip, and log by replaying those events offline. **Claim boundary:** local prototype session log only — lightweight FNV-style hashes, not production PKI, not anti-cheat, not network authority; does not change HAL geometry or SymLan gates (`proceed` / `hold` / `reverse`).
