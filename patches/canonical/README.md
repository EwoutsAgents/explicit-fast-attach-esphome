# Canonical OpenThread deltas

These patches capture the OpenThread source changes used by the stock and
targeted-unicast solution.

## Preferred-parent controller

Apply from the OpenThread directory containing `src/core`:

```bash
patch -p1 < openthread-preferred-parent-controller.patch
```

The patch provides the selected-parent API, target filtering, candidate
capture, retry/timeout state, and direct continuation to Child ID Request. The
ESPHome adapter and native CLI always request targeted unicast discovery.

The functional and diagnostic deltas are also retained separately for audit:

```text
preferred-parent-functional.patch
preferred-parent-diagnostics.patch
```

## Stock Parent Response delay diagnostic

```bash
patch -p1 < parent-response-delay-diagnostic.patch
```

This patch records OpenThread's selected randomized Parent Response delay. It
does not alter the delay or response behavior.

## OTNS ParentRank instrumentation

`otns-parent-rank.patch` preserves the existing OTNS ParentRank instrumentation
as an independent optional patch. It is not part of either solution variant.

## Supported behavior

Only normal-response routers are supported. There is no alternate router
firmware or immediate-response patch in the current solution matrix.
