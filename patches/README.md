# OpenThread patches

> **This branch** (`upgrade/esphome-2026.10-idf-5.5.6`) targets OpenThread commit
> `43cc05a9bcf780bd758bad53d897e2d88cf8cb75`, the revision bundled with ESP-IDF 5.5.6
> (ESPHome 2026.10.2). The paper's results were built from the patches at tag
> `paper-n100-2026-09` (OpenThread `a12ff0d0`, ESP-IDF 5.5.4).

Every patch is generated with `git diff` against `43cc05a9` and applies strictly
(`git apply`, no fuzz). Nothing patches OpenThread during the firmware build any more:
`scripts/prepare_ot_overrides.py` builds one patched copy of ESP-IDF's `openthread`
component per group under `build/ot-override/<group>/`, and the ESPHome component
`thread_openthread_source` selects a group for a firmware.

## Groups

| Group | Patches (in order) | Used by |
|---|---|---|
| `delay-log` | `canonical/parent-response-delay-diagnostic.patch` | Stock-Attach, reduced-TX-power and Explicit-Attach routers |
| `explicit-attach` | `canonical/openthread-preferred-parent-controller.patch` + controller enabled in the MTD config | Explicit-Attach ED (routers unmodified) |
| `fast-attach` | `fast-attach/openthread-fast-attach-pr13121.patch` | Fast-Attach ED and routers |
| `explicit-fast-attach` | `fast-attach-ucast-1/openthread-fast-attach-pr13121.patch`, `fast-attach-ucast-1/openthread-preferred-parent-controller.patch`, `fast-attach-ucast-1/fast-attach-ucast-1-delta.patch` + controller enabled in the MTD config | Explicit-Fast-Attach ED and routers |
| `fast-attach-ucast-32` | same structure, from `fast-attach-ucast-32/` | discontinued 32 ms variant (not in the paper) |

The Stock-Attach ED uses ESP-IDF's built-in OpenThread unchanged.

## How the patches were made

- **Fast Attach** (`fast-attach/`): the source changes of OpenThread PR #13121 at head
  `2b274799` (`src/` and `include/`, without the API-version bump and tests), applied
  onto `43cc05a9` by three-way merge without conflicts, plus one router log line
  (`ParentResponseDelay delay_ms=… scan_mask=… child=…`) that the analyzer uses for the
  Net column. The PR's change is identical to the head `61034b8a` used for the paper
  apart from the API version number. Unlike the paper's backport, this one keeps the
  PR's compile guards and its `mle fastattach` CLI command (inactive in ESPHome builds).
- **Controller** (`canonical/`): the paper's controller patch, cherry-picked onto
  `43cc05a9` by three-way merge, plus upstream's rename of
  `Ip6::Address::SetToLinkLocalAddress` to `InitAsLinkLocalAddress` (#13169).
- **Explicit-Fast-Attach** (`fast-attach-ucast-1/`): applied as PR → controller → delta.
  The controller patch here is the canonical one rebased onto the PR; its only
  conflict (both features act after a successful Child ID Response) keeps both blocks.
  The delta replaces the router's response jitter with a fixed 1 ms delay for unicast
  Parent Requests that carry the Fast Attach flag; multicast requests keep the PR's
  `min(500 ms, N_AR × 32 ms)` jitter.

## OTNS (not part of the paper)

| Path | Built on |
|---|---|
| `otns/preferred-parent-cli-adapter.patch` | `canonical` controller |
| `otns/plain-fast-attach-native-adapter.patch` | `fast-attach/` (adds auto re-arm after detach and two log lines) |
| `otns/fast-attach-ucast-1-native.patch` | combined: Explicit-Fast-Attach chain + CLI adapter |

`scripts/build_otns_native_variants.sh` applies them; see `otns/README.md`.

## Other files (not applied)

| Path | Status |
|---|---|
| `canonical/otns-parent-rank.patch` | Optional OTNS visualisation aid (old base). |
| `canonical/preferred-parent-functional.patch`, `canonical/preferred-parent-diagnostics.patch` | Earlier split of the controller patch, kept for audit (old base). |
| `openthread-preferred-parent-api.patch` | Earliest API draft. |
| `provenance/phase-3.json`, `phase-3-openthread-base-selection.md` | OTNS base-selection notes. |
| `*-summary.md` | Change notes for the superseded ESPHome-owned controller design. |
| `openthread-native-preferred-parent-migration.md` | Describes the current architecture: the operation runs inside OpenThread's MLE Attacher. |
