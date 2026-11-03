# ESPHome Thread Parent Info external component

From `EwoutBergsma/ESPHome-Thread-ED-Switch-Parent` (`components/thread_parent_info`),
unchanged apart from this README and the example: it already uses ESPHome 2026.10's
`InstanceLock` API and only public OpenThread functions, so it needs no OpenThread patch.

This external component exposes the current Thread parent as ESPHome diagnostic text sensors:

- `parent_extaddr`: current parent IEEE 802.15.4 extended address, formatted as 16 lowercase hex digits.
- `parent_rloc16`: current parent RLOC16, formatted as four lowercase hex digits.

It is intended for Thread end devices using ESPHome's `openthread:` component. It uses the same OpenThread calls as the working template lambda version:

- `otThreadGetDeviceRole(instance)`
- `otThreadGetParentInfo(instance, &parent)`

## YAML usage

```yaml
external_components:
  - source: github://EwoutsAgents/explicit-fast-attach-esphome
    components: [thread_parent_info]

text_sensor:
  - platform: thread_parent_info
    update_interval: 30s
    parent_extaddr:
      name: "Parent Extended Address"
    parent_rloc16:
      name: "Parent RLOC16"
```

Set `event_based: true` to update on OpenThread state changes (a parent switch
publishes immediately) instead of polling every `update_interval`. It registers an
OpenThread state-change callback; ESP-IDF 5.5.6 allows three on an end device and
ESPHome's own OpenThread component uses one.

## Runtime behavior

The component publishes:

- `no parent` when the OpenThread role is not `OT_DEVICE_ROLE_CHILD`.
- `parent unavailable` when `otThreadGetParentInfo()` fails.
- `OpenThread not enabled` if the component is compiled without `USE_OPENTHREAD`.

If the OpenThread instance lock cannot be acquired quickly, the component skips that update rather than replacing the last known state. This matches the behavior of returning `{}` from a template text-sensor lambda.
