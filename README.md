# explicit-fast-attach-esphome

ESPHome external components for Explicit Parent Switching on Thread end devices
(Explicit-Attach and Explicit-Fast-Attach) and the OpenThread Fast Attach baseline.

This repository contains only what ESPHome needs: `components/` and the OpenThread
`patches/` they apply, so installs stay small. Documentation, the test harness,
measurement data and the paper material live in
[EwoutsAgents/explicit-fast-attach-dev](https://github.com/EwoutsAgents/explicit-fast-attach-dev).

Generated from explicit-fast-attach-dev branch `upgrade/esphome-2026.10-idf-5.5.6`,
commit `ab3ba802`.

## Use

```yaml
esp32:
  variant: esp32c6
  framework:
    type: esp-idf
    version: 5.5.6          # required

external_components:
  - source: github://EwoutsAgents/explicit-fast-attach-esphome
    components: [thread_openthread_source, thread_fast_attach_ucast_1]
```

| Component | Variant |
|---|---|
| `thread_preferred_parent` | Explicit-Attach (ED only; routers unmodified) |
| `thread_fast_attach_ucast_1` | Explicit-Fast-Attach (ED and routers) |
| `thread_fast_attach` | Fast-Attach (OpenThread PR #13121; ED and routers) |
| `thread_fast_attach_ucast_32` | 32 ms unicast variant (not in the paper) |
| `thread_parent_response_delay_log` | logging-only router diagnostic |

`thread_openthread_source` is loaded automatically. On the first compile it copies
ESP-IDF's `openthread` component into the device's own build folder and patches only
that copy; ESPHome's ESP-IDF install is never modified.

Requirements: ESPHome 2026.10.x, ESP-IDF 5.5.6, the native ESP-IDF toolchain (default),
and `git` on the PATH. Other versions are rejected during config validation with an
explanation.
