# Thread Ping (current parent)

ESPHome external component that pings the current OpenThread parent of a Thread end
device, once or automatically at an interval, and publishes the result: round-trip time,
RSS of the reply, sent/received/loss, and the target's ExtAddr, RLOC16 and address.

Adapted from `EwoutBergsma/ESPHome-Thread-ED-Switch-Parent` (`components/thread_ping`).
Difference: the original patched OpenThread (through a PlatformIO script) to add `mRss` to
`otPingSenderReply`. This version needs **no OpenThread patch**: it reads the RSS of the
reply with OpenThread's public `otThreadGetParentLastRssi()` in the reply callback (the
reply is the last frame received from the parent). It works with ESPHome 2026.10's native
ESP-IDF toolchain and leaves ESP-IDF untouched. The OpenThread CLI `ping` output is not
changed (ESPHome builds have no OpenThread CLI).

## Example

```yaml
external_components:
  - source: github://EwoutsAgents/explicit-fast-attach-esphome
    components: [thread_openthread_source, thread_fast_attach_ucast_1, thread_ping]

thread_ping:
  id: parent_pinger
  auto_start: true        # start pinging at boot
  auto_interval: 10s
  timeout: 3000ms

  state:
    name: "Thread Parent Ping State"
  last_result:
    name: "Thread Parent Ping Result"
  target_extaddr:
    name: "Thread Parent Ping Target ExtAddr"
  rtt:
    name: "Thread Parent Ping RTT"
  rss:
    name: "Thread Parent Ping RSS"
  loss:
    name: "Thread Parent Ping Loss"

switch:
  - platform: thread_ping
    thread_ping_id: parent_pinger
    name: "Thread Parent Ping"
```

Optional entities: `state`, `last_result`, `target_extaddr`, `target_rloc16`,
`target_address` (text sensors); `sent`, `received`, `loss`, `rtt`, `rss` (sensors).
A `button` platform toggles pinging on/off.

## Logs

```text
[I][thread_ping:...]: Parent ping #4 reply: icmp_seq=17 rtt=26 ms size=16 rss=-50 dBm target=...
[I][thread_ping:...]: Parent ping #4 result: success; target ExtAddr=... RLOC16=7000 ...; sent=1 received=1 loss=0% rtt=26 ms rss=-50 dBm ...
```

The ping always targets the device's *current* parent, so after an Explicit-Fast-Attach
switch the next ping goes to the new parent. If RSS is unavailable, the `rss` sensor
publishes `NaN` and the log shows `rss=unavailable`.
