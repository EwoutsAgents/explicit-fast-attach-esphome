# OpenThread-owned preferred-parent migration

## Ownership change

The preferred-parent operation now lives in OpenThread's `Mle::Attacher`.
ESPHome and OTNS only configure a target, call the public API, and render status
or callback events. The following ESPHome responsibilities were removed:

- component-loop operation state machine;
- Parent Response callback queue and candidate buffer;
- `millis()` retry and attach timers;
- selected-candidate continuation calls;
- callback-side FreeRTOS synchronization;
- fallback selection hooks and weak-symbol probing.

The canonical functional source is
`patches/canonical/openthread-preferred-parent-controller.patch`. Both the
ESPHome pre-build action and the OTNS isolated build consume this exact file.

## Public API

The experimental API is enabled by
`OPENTHREAD_CONFIG_EXPERIMENTAL_PREFERRED_PARENT_ENABLE=1` and declared in
`<openthread/preferred_parent.h>`:

```c
otThreadPreferredParentSetCallback(instance, callback, context);
otThreadPreferredParentStart(instance, &config);
otThreadPreferredParentCancel(instance);
otThreadPreferredParentClear(instance);
otThreadPreferredParentGetStatus(instance, &status);
```

`Start` is valid only for an attached child. It rejects an active attach or
preferred-parent operation with `OT_ERROR_BUSY`. Target bytes use normal
`otExtAddress::m8` display order. Retry and attach timeout fields are
milliseconds. Terminal status persists until another start or `Clear`.
Callbacks are synchronous and observational; mutating the operation from a
callback is unsupported.

Cancellation stops the Attacher timer, restores receiver state, invalidates
both candidate objects, and preserves the pre-existing child attachment.

## Native CLI

The native adapter exposes:

```text
prefparent switch <extaddr> multicast
prefparent switch <extaddr> unicast
prefparent status
prefparent cancel
prefparent clear
```

Compact, colon-separated, and hyphen-separated addresses are accepted.
Events use stable `PREFPARENT key=value` output and include the operation
generation, attempt, state, target, mode, error, and OTNS event timestamp.

## Compatibility notes

`parent_extaddr` is the authoritative target form. The ESPHome adapter retains
`parent_rloc` only as a compatibility convenience and resolves it from the
current OpenThread neighbor table before calling the extended-address API. It
fails explicitly if that router is not already present in the table.

`require_selected_parent_hook` remains accepted by ESPHome YAML for migration
but is now a no-op: the build has a compile-time dependency on the public API.
`log_parent_responses` remains accepted for configuration compatibility but is
ignored. Structured controller events are always logged; application-side
Parent Response logging and buffering no longer exist.

The older functional, diagnostic, and CLI-controller patches remain archived
as design evidence. They are not used by the new isolated build profiles.
