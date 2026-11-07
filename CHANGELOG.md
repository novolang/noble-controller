# Changelog

Every published version, newest first. This file is on the publish
allow-list, so it travels with the package: it is the only thing a
consumer deciding whether to upgrade can read.

## Unreleased

`ll_cs_plan.sync_ns` takes the length of a CS_SYNC packet from `ll_cs_radio.cs_sync_bits` and `cs_sync_bit_ns`.  The figures do not change (44 microseconds on LE 1M and 26 on LE 2M and LE 2M 2BT for an access address alone).  The profile `ctl_cs` turns `ctl_cs_mode3` and `ctl_cs_rtt_seq` on, so the Controller's tests of mode 3, of the sounding and random sequences and of LE 2M run under it; a radio that does not report them still cuts them out of the capabilities.

`ll_cs_plan.gen_new`, `gen_instantiate_test`, `gen_begin_procedure`, `plan_new`, `plan_subevent` and `plan_arm` are public, so that a
program that drives a radio without the Controller (the Channel Sounding bench rig of `orbit/ble`) can plan the subevent of an
`LE CS Test` and hand it to a `CsRadio`.  No behaviour changes.

`ll_cs_air` is the Channel Sounding slot of the radio program: `cs_poll`, which an image's main loop calls after `ll_poll` with the planning storage (`ll_cs_plan.CsState`) and the record (`ll_cs_air.CsAir`) the image holds, reads the radio's capabilities once, runs the subevents of an `LE CS Test` and plans and runs the subevents of the procedures of a connection at the times the Start fixed, on any radio that implements `Radio`, `Timebase` and `CsRadio`.  It is removed with `ctl_cs` 0, which links none of it.  `ctl_cs_subevent` is split into `ctl_cs_subevent_plan` (the planning, which takes milliseconds) and `ctl_cs_subevent_run`; `ctl_cs_series_open`, `ctl_cs_sched`, `ctl_cs_event_time`, `ctl_cs_test_count`, `ctl_cs_test_interval_us`, `ctl_cs_test_len_us` and `ctl_cs_result_waiting` read the state the slot schedules from.  A Central that answers a Channel Sounding Start picks the offset of the first subevent 3 ms after the anchor point when the window allows (it took the window's start), and a Peripheral answers the request with the part of its window from there on (it repeated the window).  The plan carries the peer's FAE table and the CS_SYNC antenna selection, and the storage the keys state grows by 96 octets (`ctl_cs_steps`: 136 + 96 per step).  `ll_air.stop_rx` is public.  With `ctl_cs` 0 nothing changes.

## 0.1.0

First release.  The portable Link Layer and HCI command handler of the noble
Bluetooth stack, extracted from `orbit/ble` (`src/controller/`): the
advertising, scanning, initiating and connection states of both roles,
extended and periodic advertising, connected and broadcast isochronous
channels, LE encryption, privacy, power control, subrating and the other LE
features of Core 6.3, and the HCI command layer over them.  The radio, the
clock, the cipher and the ECDH engine are reached through `noble-radio`; the
HCI wire is read through `noble-hci`.

The 24 `ctl_*` keys of the `orbit/ble` configuration are the schema of this
package, under the section `[noble-controller]`; the constants are read as
`noble_controller_config.CTL_*`.

The public surface is what a Host package and a chip image call: the `Controller` of `ctl_hci` with its constructor, its
HCI stream, its main-loop and judgement functions and the work it owes the chip; the radio program's entry `ll_poll` of
`ll_air` and its state; `LinkPolicy` and its default of `ll_policy`; and the records and constants those read.  The
unit tests are in `tests/` and do not ship, and every `.nv` file is what `novo fmt` prints.
