# Phase 3 OpenThread base selection

> **Not part of the paper.** These are working notes on choosing the OpenThread base for the OTNS port. The hardware firmware uses the OpenThread revision vendored by ESP-IDF 5.5.4 (`a12ff0d0`).

## Verdict

**VALIDATED — use Track A.**

Use the hardware OpenThread revision as the native OTNS/RFSIM port base:

```text
a12ff0d0f54fd41954b45047fcdd08f302731c5f
```

The exact revision builds and runs with the current OTNS RFSIM platform without
OpenThread source changes or RFSIM compatibility patches. This removes the
830-commit OpenThread version difference from the first hardware/simulation
comparison.

Track B, the OTNS submodule revision `7874555efb1772...`, remains a fallback if
a later required OTNS feature cannot be supported on Track A without substantial
work.

## Question tested

Can OTNS commit `099a6c26cb1d2b8749d3171d5cdd8597fc71049c` build and run
native MTD and FTD executables from the hardware OpenThread revision without
substantial compatibility changes?

The acceptance gates were:

1. configure the current RFSIM platform against a clean Track A checkout;
2. build both `ot-cli-mtd` and `ot-cli-ftd` with PPS disabled;
3. start both executable families in OTNS;
4. form a two-router Thread topology and attach a MED;
5. remove the MED's observed parent;
6. observe recovery to the surviving router within 360 simulated seconds.

## Build experiment

The OpenThread checkout was detached at `a12ff0d0...`, including its Mbed TLS
submodules. The current `ot-ns/ot-rfsim/script/build` entry point was used with:

```bash
PATH=/home/ewout/.platformio/packages/tool-ninja:$PATH \
OT_DIR=/path/to/openthread-a12 \
OTNS_NODE_TYPE=espidf-a12-stock \
OT_CMAKE_BUILD_DIR=build/espidf-a12-stock \
OT_CMAKE_NINJA_TARGET='ot-cli-ftd ot-cli-mtd' \
./script/build \
  -DCMAKE_C_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=0 \
  -DCMAKE_CXX_FLAGS=-DOPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE=0
```

Result:

- CMake configuration passed;
- all 754 Ninja build steps passed;
- `ot-cli-mtd` and `ot-cli-ftd` linked successfully;
- no OpenThread or RFSIM source file was changed;
- no warning-as-error or platform API incompatibility occurred.

Two initial setup failures were excluded from the compatibility assessment:
Ninja was not on the shell `PATH`, and the throwaway Git checkout initially
lacked its nested Mbed TLS submodules. Both are build prerequisites, not source
incompatibilities.

Toolchain used:

```text
Linux 6.17.0-29-generic x86_64
GCC 13.3.0
CMake 3.28.3
Ninja 1.13.1
```

Binary fingerprints:

| Binary | Size | SHA-256 |
| --- | ---: | --- |
| `ot-cli-mtd` | 33,448,320 bytes | `d13e4d1a2e7699b0448a5902c577fe26276552fb2c49ba5e88bce6dc7d4fc823` |
| `ot-cli-ftd` | 46,965,216 bytes | `a5c2b9c9e937252f8774d879589d53fd459cd04e9561fcdcf5502700d5a939b5` |

These hashes identify this feasibility build only. Phase 8 will generate the
canonical binary matrix and its durable build manifests.

## Runtime experiment

The OTNS-MAPS scenario
`scenarios/static/med_static_parent_removal_2routers.yaml` was run twice using
the Track A FTD for both routers and the Track A MTD for the child. The second
run explicitly used OTNS random seed `2303`.

Both runs produced the same required observations:

- Router A and Router B formed the initial topology;
- the MED attached to Router A;
- Router A, the observed parent, was deleted at simulation time 305 s;
- the MED attached to Router B at simulation time 542 s;
- post-removal recovery latency was 237 simulated seconds;
- the MED ended in the `child` role;
- the run was classified as `switch_observed`;
- the final parent probe delivery ratio was 1.0.

The long 237-second stock recovery is a behavioral baseline, not a platform
failure. It is within the contract's 360-second observation window and is one
of the behaviors the selected-parent variants are intended to improve.

## Isolation decision

Conflicting variants will not share a mutable OpenThread source tree. Each
variant will have:

- a clean worktree at `a12ff0d0...`;
- only its own canonical patches applied;
- a distinct CMake output directory;
- separately fingerprinted MTD and/or FTD executables.

A shared Git object store is acceptable because worktree files and build trees
remain isolated. OTNS launches nodes as separate processes, so executables from
different variant trees can coexist in one simulation. Homogeneous campaigns
will use family-wide `exe mtd` and `exe ftd` selection; mixed experiments may
use per-node `add ... exe ...` selection.

This preserves the hardware campaign's multiple-instance model while avoiding
full duplicate Git clones.

## Consequence for Phase 4

Phase 4 should port the selected-parent behavior directly onto clean Track A
worktrees. The canonical hardware patches already use that base, but they must
still be reviewed and divided into native core, controller, and diagnostic
changes. The uninitialized candidate-snapshot defect identified in Phase 1 must
be corrected rather than reproduced.

The independent `ParentRank` patch targets Track B and must not be applied
blindly to Track A. Re-port that instrumentation only after the functional
selected-parent path passes.

