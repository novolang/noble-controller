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
   `ll_past`) decide what to send and when.  They hold the state and the
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

The schema is the `[config.<key>]` tables of `novo.toml`: 24 keys, each
named `ctl_<what>` (`ctl_links`, `ctl_peripheral`, `ctl_central`, `ctl_cis`,
`ctl_cigs`, `ctl_bigs`, `ctl_bis`, `ctl_adv_sets`, `ctl_adv_data`,
`ctl_per_adv`, `ctl_per_sync`, `ctl_per_list`, the PAwR keys, and one
switch for each optional LE feature).  The ranges are the bounds of the
Core Specification where it states one; a relation between keys (a stream
needs a group, a train needs an advertising set) is a field of the schema,
and `novo config check` refuses a file that breaks it.

A key that is `0` or `false` switches its feature off: `ctl_limits` reports
the feature as out, `ctl_hci` answers its commands with Unknown HCI Command
and leaves its LE feature bit clear, and a table of the feature keeps one
slot.  `ctl_budget` adds the storage of the tables up and an `assert_const`
holds the sum to the total `novo config explain` prints.

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
