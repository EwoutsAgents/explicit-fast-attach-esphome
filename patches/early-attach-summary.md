# v19 early attach summary

> **Historical, superseded.** This note describes an earlier design that has been replaced by the OpenThread-owned controller in [`openthread-native-preferred-parent-migration.md`](openthread-native-preferred-parent-migration.md). It is kept for reference and is not part of the paper.

This update adds target-triggered early attach for both multicast and unicast discovery. v19 also fixes the OpenThread patcher so the early-attach interrupt block does not declare an initialized local variable below a `VerifyOrExit(...)` macro; this avoids the ESP-IDF/OpenThread compile error `jump to label exit crosses initialization`.

## YAML

```yaml
thread_preferred_parent:
  parent_request_unicast: false
  early_attach_on_target: true
  early_attach_delay: 250ms
```

## Behavior

When `early_attach_on_target` is enabled, the ESPHome component shortens the discovery window as soon as the requested target parent is observed. Instead of waiting for the full `retry_interval`, it waits `early_attach_delay` and then starts selected-parent attach.

The OpenThread patcher also allows `AttachToSelectedParent()` to interrupt the component-owned discovery-only `SearchForBetterParent()` pass. This avoids `kErrorBusy` when early attach starts before OpenThread's own discovery timer has completed.

## Logging

Discovery now logs the target-observed time and total discovery time before attach, for example:

```text
Target Parent Response observed after 320 ms during discovery; early selected-parent attach scheduled in 250 ms
Discovery summary (early target debounce complete): 1 Parent Responses, 1 target match(es), best target RLOC16 0x1800 RSSI -70
Discovery result: target observed after 320 ms; starting selected-parent attach after 570 ms total discovery time (250 ms early-attach delay)
Attach result: success after 811 ms; ExtAddr 32a4d516437f9aab selected
```
