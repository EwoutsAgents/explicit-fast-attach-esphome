# explicit-fast-attach-dev — ESPHome components (install branch)

This branch contains only what ESPHome needs to install the components: `components/`
and the OpenThread `patches/` they apply. Everything else (documentation, test harness,
measurement data, paper material) lives on the development branches of
[EwoutsAgents/explicit-fast-attach-dev](https://github.com/EwoutsAgents/explicit-fast-attach-dev).

Generated from branch `upgrade/esphome-2026.10-idf-5.5.6`, commit `f4bd5055`.

## Use

```yaml
esp32:
  variant: esp32c6
  framework:
    type: esp-idf
    version: 5.5.6          # required

external_components:
  - source: github://EwoutsAgents/explicit-fast-attach-dev@esphome
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
