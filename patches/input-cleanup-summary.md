# Input cleanup v17

> **Historical, superseded.** This note describes an earlier design that has been replaced by the OpenThread-owned controller in [`openthread-native-preferred-parent-migration.md`](openthread-native-preferred-parent-migration.md). It is kept for reference and is not part of the paper.

Changes:

- Clearing the Home Assistant RLOC16 text input now clears the RLOC16 target instead of configuring `0x0000`.
- `0x`-prefixed RLOC16 values remain accepted, for example `0x1800` and `1800` both parse as RLOC16 `0x1800`.
- With `parent_request_unicast: true`, an ExtAddr target still uses unicast Parent Request discovery.
- With `parent_request_unicast: true` and an RLOC16 target that cannot yet be resolved to an ExtAddr, the component now falls back to multicast Parent Request discovery instead of failing with `OT_ERROR_NOT_FOUND`. If the target RLOC16 responds, the selected-parent attach still uses the observed ExtAddr from that Parent Response.
