# Changelog

Every published version, newest first. This file is on the publish
allow-list, so it travels with the package: it is the only thing a
consumer deciding whether to upgrade can read.

## Unreleased

A Central starts the subevents of every stream after the first of its group 16 microseconds before their time on the group's grid (`ctl_hci.CIS_LATER_TRIM_US`, applied by `ctl_cis_start`).  The PTS dongle, as the Peripheral, places the first event of a later stream from the earlier stream's timeline and listens in a window of about 40 microseconds that lies before the nominal time; with the trim the second stream of a group of two failed to establish (LE CIS Established 0x3E) in 2 of 12 runs of four BAP/UCL/STR rows against 12 of 16 without it.  The trim is measured against that Peripheral only.

The Link Layer keeps a record of the control PDUs of the Data Length Update procedure (`ll_link.dle_note`, `dle_rec_field`): the newest LL_LENGTH_REQ and LL_LENGTH_RSP this end queued and the newest it heard, each with the connection event, the four values and an outcome code (taken, out of range, answered no request, queue full), the newest refusal with its opcode and reject code, the kind written last, and five counters.  The record is 10 words, 6 counters and the kind written last in each `Link` (3,144 to 3,288 octets in the build report of the rig image) and is read through the image's status line (`ll dle`).  No behaviour changes.

`ll_cs_plan.sync_ns` takes the length of a CS_SYNC packet from `ll_cs_radio.cs_sync_bits` and `cs_sync_bit_ns`.  The figures do not change (44 microseconds on LE 1M and 26 on LE 2M and LE 2M 2BT for an access address alone).  The profile `ctl_cs` turns `ctl_cs_mode3` and `ctl_cs_rtt_seq` on, so the Controller's tests of mode 3, of the sounding and random sequences and of LE 2M run under it; a radio that does not report them still cuts them out of the capabilities.

`ll_cs_plan.gen_new`, `gen_instantiate_test`, `gen_begin_procedure`, `plan_new`, `plan_subevent` and `plan_arm` are public, so that a
program that drives a radio without the Controller (the Channel Sounding bench rig of `orbit/ble`) can plan the subevent of an
`LE CS Test` and hand it to a `CsRadio`.  No behaviour changes.

`ll_cs_air` is the Channel Sounding slot of the radio program: `cs_poll`, which an image's main loop calls after `ll_poll` with the planning storage (`ll_cs_plan.CsState`) and the record (`ll_cs_air.CsAir`) the image holds, reads the radio's capabilities once, runs the subevents of an `LE CS Test` and plans and runs the subevents of the procedures of a connection at the times the Start fixed, on any radio that implements `Radio`, `Timebase` and `CsRadio`.  It is removed with `ctl_cs` 0, which links none of it.  `ctl_cs_subevent` is split into `ctl_cs_subevent_plan` (the planning, which takes milliseconds) and `ctl_cs_subevent_run`; `ctl_cs_series_open`, `ctl_cs_sched`, `ctl_cs_event_time`, `ctl_cs_test_count`, `ctl_cs_test_interval_us`, `ctl_cs_test_len_us` and `ctl_cs_result_waiting` read the state the slot schedules from.  A Central that answers a Channel Sounding Start picks the offset of the first subevent 3 ms after the anchor point when the window allows (it took the window's start), and a Peripheral answers the request with the part of its window from there on (it repeated the window).  The plan carries the peer's FAE table and the CS_SYNC antenna selection, and the storage the keys state grows by 96 octets (`ctl_cs_steps`: 136 + 96 per step).  `ll_air.stop_rx` is public.  With `ctl_cs` 0 nothing changes.

The arbiter has two classes more for Channel Sounding in a build with `ctl_cs`: `ll_arb.class_cs()` and `class_cs_next()`.  The classes of the links are `ll_arb.class_acl()` plus the slot; the constants `CLASS_ACL`, `CLASS_ACL2` and `CLASS_ACL3` are gone, since the first class of a link moves up by one in a build with the feature.  A build without it keeps every class number, and its images are the same to the octet.  `ll_cs_fit` places a Channel Sounding Start among the connection events and the streams: `schedule_ok` of the procedures no longer agrees to every Start, the Controller re-suggests the connection event, the interval of events, the subevent length and the window of offsets where Section 5.1.26 allows, and `start_from_pp` proposes a Subevent_Len of at most 5 ms.  The slot `cs_poll` books each subevent in the arbiter, gives up one that does not fit as a subevent aborted for a scheduling conflict, and no longer waits 2.5 ms after a run (`ctl_cs_room` holds the HCI stream back instead).  `ctl_cs_subevent_skip`, `ctl_cs_fits`, `ctl_cs_book`, `ctl_cs_unbook`, `ctl_cs_room`, `ctl_cs_lead_us` and `ctl_cs_event_on_grid` are new.

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
