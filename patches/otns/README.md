# Native OTNS OpenThread patches

> **Not part of the paper.** The paper reports hardware measurements only. This OTNS (OpenThread Network Simulator) port is kept for further work; see the root [README](../../README.md).

These patches target OpenThread commit:

```text
a12ff0d0f54fd41954b45047fcdd08f302731c5f
```

## Native CLI adapter

The reproducible build uses the canonical public controller followed by the
native CLI adapter:

```bash
git -C /path/to/openthread apply \
  /path/to/patches/canonical/openthread-preferred-parent-controller.patch
git -C /path/to/openthread apply \
  /path/to/patches/otns/preferred-parent-cli-adapter.patch
```

The adapter accepts only unicast selected-parent operations. Router binaries
retain ordinary OpenThread Parent Response scheduling.

## Reproducible binary set

Run:

```bash
OPENTHREAD_REPOSITORY=/path/to/full/openthread-repository \
OTNS_RFSIM_DIR=/path/to/ot-ns/ot-rfsim \
OTNS_VARIANT_ROOT=/new/path/to/openthread-variants \
./scripts/build_otns_native_variants.sh
```

The script publishes:

```text
artifacts/stock-mtd-pps-off/ot-cli-mtd
artifacts/preferred-parent-mtd-pps-off/ot-cli-mtd
artifacts/stock-ftd/ot-cli-ftd
artifacts/stock-ftd-delay-diagnostic/ot-cli-ftd
artifacts/fast-attach-mtd-pps-off/ot-cli-mtd
artifacts/fast-attach-ftd/ot-cli-ftd
artifacts/fast-attach-ucast-1-mtd-pps-off/ot-cli-mtd
artifacts/fast-attach-ucast-1-ftd/ot-cli-ftd
```

The delay-diagnostic FTD changes logging only. It is behaviorally a stock
router and can be used when exact randomized-delay subtraction is required.

`fast-attach-ucast-1-native.patch` is a native composition of the corresponding
ESPHome/OpenThread patch stack. It includes the preferred-parent CLI adapter used by OTNS-MAPS and avoids
order-dependent patch conflicts in `mle.cpp`.
