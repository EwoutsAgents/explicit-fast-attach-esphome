# OpenThread patch summary

> **Historical, superseded.** This note describes an earlier design that has been replaced by the OpenThread-owned controller in [`openthread-native-preferred-parent-migration.md`](openthread-native-preferred-parent-migration.md). It is kept for reference and is not part of the paper.

This component auto-patches ESP-IDF's vendored OpenThread core during the PlatformIO build.

The patch adds:

1. A parent-response callback bridge so ESPHome can log every received MLE Parent Response.
2. A discovery-only bridge that starts multicast Parent Request discovery without detaching from the current parent.
3. A selected-parent attach bridge that forces an attach to a chosen parent extended address after the target was observed.

The discovery-only path prevents the disruptive selected-parent attach from being attempted when the requested parent is not present.


## v9 selected-parent response filter

During selected-parent attach, `Mle::Attacher::HandleParentResponse()` now drops Parent Responses whose ExtAddr does not match `mParentCandidate.GetExtAddress()`. Preflight discovery remains multicast and non-disruptive; filtering is only active when `mMode == kSelectedParent`.


## v12 update

The selected-parent patch now removes the earlier forced `BecomeDetached()` block, pre-seeds the selected parent ExtAddr before `Attach(kSelectedParent)`, and adds a selected-parent-only Child ID Request bypass once the target Parent Response has populated `mParentCandidate`. This follows the biparental repository lesson that the actual control boundary is the internal OpenThread selected-parent Child ID attach, not merely observing a target Parent Response.


## v12 fix

This package fixes a clean-build ordering issue where ESP-IDF/OpenThread 5.5.4 could report `mle.cpp selected-parent candidate preseed` as missing while the old force-detach block was still present. The pre-build patcher now removes the old block before applying the preseed patch and also tolerates the legacy block if encountered.

## v16 fix

The parent-request-unicast patcher now replaces only the destination-selection branch inside `Mle::Attacher::SendParentRequest()` instead of a broad range from `AppendVersionTlv()` to `SendTo()`. This prevents the ESP-IDF/OpenThread 5.5.4 failure where `mle.cpp` could be left with an unterminated `#if`. The script also restores a previously truncated `mle.cpp` from the `.thread-preferred-parent.bak` backup before reapplying patches, and ensures the unicast discovery bridge declarations are injected before `HandleTimer()` and `SendParentRequest()` reference them.
