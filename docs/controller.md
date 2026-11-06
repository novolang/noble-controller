# Modules, configuration and the radio seam

`noble-controller` is the Controller of the noble stack: the HCI command
handler and the Link Layer, with no register and no Host code.

## What it reads

| Package | What the Controller takes from it |
|---|---|
| `noble-hci` | the opcode and event constants, the frame types and the H4 codec |
| `noble-radio` | `Radio` and `Timebase` (the radio and the clock), `Cipher` (AES-CCM of a link), `Ecdh` (the P-256 engine), and the `Pdu` and PHY types |

The Controller imports nothing else of the stack.  `tests/orbit/test_ble_core_imports_no_extension.sh`
in the repository holds the rule: no module of this package imports a module
of `orbit/ble`.

## The layers

1. **HCI.**  `h4_rx` cuts the octets the Host sends into HCI packets.
   `ctl_hci` decodes each command, answers it (Command Complete or Command
   Status), and sends the events that follow.  `ctl_pool` holds the packet
   buffers both directions share.
2. **State machines.**  `ll_adv`, `ll_scan`, `ll_init`, `ll_link`, `ll_xadv`,
   `ll_per`, `ll_pawr`, `ll_iso`, `ll_big` and the smaller procedure modules
   (`ll_feat`, `ll_fs`, `ll_pcl`, `ll_ploss`, `ll_rate`, `ll_sca`, `ll_sub`,
   `ll_past`, `ll_cs`) decide what to send and when.  They hold the state and the
   arithmetic and call no radio.
3. **The arbiter.**  `ll_arb` decides which activity holds the radio next
   and until when.
4. **The radio program.**  `ll_air` turns the decisions into events on a
   `Radio` and a `Timebase`: the order of the PDUs of an advertising event,
   the T_IFS turn-arounds, the scan, initiating and connection exchanges.
   The chip supplies the register work behind the traits.

`ll_policy` is where a product decides: the Link Layer asks `LinkPolicy`
before it accepts a connection or a request, and the product answers.

## Configuration

The schema is the `[config.<key>]` tables of `novo.toml`: 34 keys, each
named `ctl_<what>` (`ctl_links`, `ctl_peripheral`, `ctl_central`, `ctl_cis`,
`ctl_cigs`, `ctl_bigs`, `ctl_bis`, `ctl_adv_sets`, `ctl_adv_data`,
`ctl_per_adv`, `ctl_per_sync`, `ctl_per_list`, the PAwR keys, one
switch for each optional LE feature, and the ten `ctl_cs*` keys of Channel
Sounding).  The ranges are the bounds of the
Core Specification where it states one; a relation between keys (a stream
needs a group, a train needs an advertising set) is a field of the schema,
and `novo config check` refuses a file that breaks it.

A key that is `0` or `false` switches its feature off: `ctl_limits` reports
the feature as out, `ctl_hci` answers its commands with Unknown HCI Command
and leaves its LE feature bit clear, and a table of the feature keeps one
slot.  `ctl_budget` adds the storage of the tables up and an `assert_const`
holds the sum to the total `novo config explain` prints.

Channel Sounding has one count, `ctl_cs` (the connections that run it at once,
0 for a build without it), and nine keys that describe the build the count
switches on: `ctl_cs_configs`, `ctl_cs_steps`, `ctl_cs_roles` and `ctl_cs_ant`
are 0 exactly when `ctl_cs` is, and `ctl_cs_mode3`, `ctl_cs_rtt_seq`,
`ctl_cs_3c`, `ctl_cs_ipt` and `ctl_cs_test` choose among its options and need
it.  `ctl_cs` needs `ctl_pcl`, and `ctl_cs_ipt` needs `ctl_featpages`.  Three keys state storage.  `ctl_cs`: for each connection that runs the
feature, the generator of the planning (`CsGen` of `ll_cs_plan`, 712 bytes) and one record of the procedures (`ll_cs_proc`) kept in two tables of the Controller,
38 words and a store of 224 B, and once for the Controller 40 words and 160 B of store after the records (the Host Support bit, the capabilities, the parameters of an
LE CS Test, the FAE table of the test, the header of the result that waits); `ctl_cs_configs`: 56 B more of store for each configuration a connection holds (the 27
octets of its PDU and the 20 of the procedure parameters the Host set); `ctl_cs_steps`: the plan of one subevent (`CsSubevent`, 40 bytes and 56 for each step) and 40 B
for each step of the result that waits to go to the Host.  `CsState` holds the generators and the plan, and the caller of the functions that run a subevent owns it.  A build without the feature keeps the two tables of the
procedures at one element each and makes nothing else; the modules of the feature are not part of it.  The control queue of a link holds 76 octets a slot
in a build with the feature, 40 in one without it, for the 75 octets of LL_CS_FAE_RSP.  With `ctl_cs` at 0 the 18 commands are answered with Unknown HCI
Command, the 14 Link Layer opcodes (0x2D to 0x3A) with LL_UNKNOWN_RSP, and LE features 46, 47, 48 and 75 stay clear; with it on, `ll_cs` lists the commands in
Supported Commands and answers each as Core 6.3 says, and the 14 opcodes go to the seven procedures of `ll_cs_proc`, which answer them over the record of the link.

The commands and events are in `ctl_hci`, their semantics in `ll_cs_hci` and the data of a step in `ll_cs_res`.  LE Set Host Feature takes bit 47 (Channel Sounding, Host
Support), with a connection it answers Command Disallowed; without the bit the commands that list it answer Command Disallowed and the procedures reject the peer's
requests with Unsupported Remote Feature.  The commands that ask the peer (Read Remote Supported Capabilities, Security Enable, Read Remote FAE Table, Create Config with
the peer, Procedure Enable, Set Channel Classification) also need the peer's feature set, with its bits 46 and 47.  The events follow the Host's event mask (bits 43 to 50
and 55): the capabilities event is the [v2] one when the build has Enhancement #1 and the Host unmasked it, otherwise the [v1] one.  The result of a subevent waits in the
Controller as the records of its steps and goes out as a Subevent Result event and as many Continue events as it needs, each at most 255 octets of parameters, as soon as
the pool has a slot; one result waits at a time, a second is reported by its header, aborted for lack of resources, and a third is dropped and counted.

The radio's side of the feature is `CsRadio` in `noble-radio`, which the radio program does not call yet.  The caller that will (the arbiter's class of CS7, the tests) runs
a subevent with three functions of `ctl_hci`: `ctl_cs_instance` at the start of each procedure instance (the channel map of an update takes effect, CSProcCount is
incremented, the generator is keyed from the values of Security Start and ratcheted), `ctl_cs_subevent` for each subevent of it and `ctl_cs_test_subevent` for each subevent
of an LE CS Test; they plan the subevent into the `CsState` the caller holds, hand it to the radio, run it and keep the result for the Host.  `ctl_cs_radio_init` reads the
capabilities of the radio once, so that the Controller reports the intersection with its build and reports the tone quality (LE feature 48) when the radio does.

The plan of a subevent is a function of the generator's key, the configuration
and the step counter, so two Controllers that hold the same key make the same
plan (`ll_cs_drbg` and `ll_cs_plan`).  `plan_next` makes one step and
`plan_subevent` makes a subevent: the steps, with their channels, access
addresses, sequences, tone extension slots, antenna path permutations and times,
in the `CsSubevent` the Controller holds.  The tests hold the generator and the
channel selection, the access addresses and the sequences to the sample data of
Core 6.3 Vol 6 Part C, Sections 7 and 8.1.  `SimCs` in `tests/sim_cs_tests.nv` is a
simulated radio for `CsRadio`: it takes the plan of `plan_arm`, computes the tones, the
time stamps and the frequency offset of a subevent from a model of the two devices and
the distance between them, and returns them a step at a time; the same file holds the
estimator the tests use to recover the distance from the results of both devices.

`configs/<profile>.toml` are the profiles the package's tests run under.
The same names exist in `orbit/ble/configs/`, whose `[noble-controller]`
sections equal these; the script `tests/orbit/test_ble_config_equals_limits.sh`
checks the two.

## The public surface

A Host package and a chip image name 99 items of the package; they are `pub`, each with a doc comment, and every other item is
private.  `novo doc` prints them.

| Module | Public items |
|---|---|
| `ctl_hci` (57) | `Controller` and `controller_new`; the capability flags `CAP_ECB`, `CAP_RNG`, `CAP_LL`, `CAP_ECDH`; the Host's stream (`HostTx`, `ctl_rx`, `ctl_in_packet`, `ctl_tx_pending`, `ctl_tx_next`, `ctl_tx_drain`, `ctl_pool_free`, `ctl_flush_events`); the main loop (`ctl_step`, `ctl_set_time`, `ctl_set_room`, `ctl_ll_room`, `ctl_ll_book`); the judgement of a received PDU in each state (`ctl_adv_rx`, `ctl_scan_rx`, `ctl_scan_decide`, `ctl_scan_note`, `ctl_init_decide`, `ctl_connect_ind` and the others); the work the chip owes (`ctl_entropy_*`, `ctl_async_*`, `ctl_ecdh_*`, `ctl_privacy_*`, `ctl_secure_*`, `ctl_big_*`) |
| `ll_air` (5) | `ll_poll`, the radio program's entry, its state `Rf` with `rf_new` and `reset_window`, and `air_profile` |
| `ll_policy` (3) | `LinkPolicy`, the product's say in taking a connection, `DefaultLinkPolicy` and `default_link_policy` |
| `ll_privacy` (8), `ll_adv` (4), `ll_iso` (4), `ll_scan` (3), `ll_arb` (2), `ctl_pool` (2), `ll_big`, `ll_ccm`, `ll_link` (1 each) | the records and constants the glue reads, among them `rl_new` and `rl_add` of the resolving list and `soft_cipher_new` |
| `ctl_limits` (6), `ll_per`, `ll_xadv` | the derived limits the images size their tables with (`cis_slots`, `big_slots`, `bis_slots`, `arb_classes`, `big_on`, `per_on`) and the aliases `PerData` and `AdvData` |

The configuration module `noble_controller_config` is generated from the keys of `novo.toml`; a consumer reads its constants
and sets them in its own config file.

## Tests

`tests/<module>_tests.nv` holds the unit tests of each module that has logic
of its own, and `src/` ships none.  The other suites in `tests/` drive
the whole Controller: `ctl_hci_tests` (the command layer), `ctl_ll_tests`,
`ctl_conn_tests`, `ctl_central_tests`, `ctl_llcp_tests` and `ctl_enc_tests`
(the connection, the Central role, the control procedures, encryption),
`ctl_iso_tests`, `ctl_pcl_tests`, `ctl_air_tests` (the radio program on a
scripted `Radio` with no registers), and `ll_privacy_tests`.

`novo pkg publish` runs every suite under the minimum configuration, the maximum configuration and each file of
`configs/`.  A test whose subject a configuration leaves out does not exist there: it carries `@when` on the keys it
needs, for example `@when(noble_controller_config.CTL_CENTRAL > 0)` above a test that opens a connection as Central, and the
build under `ctl_central = 0` does not compile it.  A test that reads a limit computes the figure it expects from the
configuration key (`ctl_limits.data_max()`, `noble_controller_config.CTL_ADV_SETS`) and not from the default.
