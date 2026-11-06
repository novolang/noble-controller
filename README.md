# noble-controller

The Link Layer and the HCI command handler of the noble Bluetooth Low Energy
stack.  The package answers the Host's HCI commands, runs the Link Layer
state machines (advertising, scanning, initiating, connections, isochronous
streams, periodic advertising, encryption, power control, subrating) and
tells the radio what to do next.  It holds no register: the radio, the clock,
the block cipher and the ECDH engine are reached through the traits of
`noble-radio`, and the HCI seam is read through `noble-hci`.  A chip package
implements the traits, and the same Controller then runs on it.

| Module | Holds |
|---|---|
| `ctl_hci` | the Controller: the HCI commands it answers, the events it sends, and the state those commands set |
| `ctl_pool` | the packet buffers: a fixed pool of slots, the queue of the slots that wait to be sent, and the builder of an event packet |
| `h4_rx` | the Controller's side of the H4 transport: the octets the Host sends, cut into HCI packets |
| `ctl_limits` | the values the configuration derives: which features are in, the number of slots of each table, the octets of the LE feature set |
| `ctl_budget` | the RAM the configured tables add up to, held to the total `novo config explain` prints |
| `ll_air` | the radio program: the advertising, scan, initiating and connection events, run on any `Radio` and `Timebase` |
| `ll_adv`, `ll_scan`, `ll_init`, `ll_link`, `ll_arb` | the advertising, scanning and initiating states, the connection state of both roles, and the arbiter that decides which activity holds the radio next |
| `ll_xadv`, `ll_ext`, `ll_per`, `ll_past`, `ll_pawr` | extended advertising, periodic advertising and its synchronization, sync transfer, and periodic advertising with responses |
| `ll_iso`, `ll_big` | connected isochronous streams and broadcast isochronous groups |
| `ll_data`, `ll_privacy`, `ll_dtm`, `ll_policy` | the data channel PDUs, the resolving list and resolvable private addresses, Direct Test Mode, and the points where a product decides |
| `ll_feat`, `ll_fs`, `ll_pcl`, `ll_ploss`, `ll_rate`, `ll_sca`, `ll_sub` | feature pages, frame space update, power control, path loss monitoring, connection rate, sleep clock accuracy and connection subrating |
| `ll_cs` | Channel Sounding: the opcodes, event codes, feature bits and limits of Core 6.3 and the tables of its HCI commands; NOT IMPLEMENTED: the procedures, the results and the measurements, so a build with the feature on answers each command with Unsupported Feature or Parameter Value |
| `ll_cs_drbg` | the random bit generator of Channel Sounding: the AES-based key and nonce, the draws of bits and of a number in a range, and the ratchet between procedures |
| `ll_cs_plan` | the plan of a Channel Sounding subevent: the channel lists, the access addresses, the sounding and random sequences, the tone extension slots, the antenna path permutations, the step timeline and the cut into subevents, held in storage the keys size, and its hand-over to a `CsRadio` |
| `ll_aes`, `ll_ccm`, `ll_cmac` | AES-128, AES-CCM and AES-CMAC in software, for a chip that has no engine |

A Controller is generic over the traits it drives, so the program costs the
effects of the backend and no call goes through a table.

```novo norun:bad
use ctl_hci
use ll_air

// The main loop of a Controller image, abridged from controller/hci_uart_main.nv of the package noble-examples: the
// HCI layer takes the commands the Host sent, then the Link Layer runs the next radio event
// on whatever `Radio`, `Timebase` and `Cipher` the image gives it.
ctl_hci.ctl_set_time(var c, air.now_us())
ctl_hci.ctl_set_room(var c, ctl_hci.ctl_ll_room(var c, air.now_us()))
let _ran = ctl_hci.ctl_step(var c)
ll_air.ll_poll(var air, var c, var rf, var rx, var policy, var cc)
```

The sizes of the tables are keys of the package configuration.  A consumer
writes a `[noble-controller]` section in its config file (the `ctl_*` keys:
`ctl_links`, `ctl_cis`, `ctl_bigs`, `ctl_adv_sets`, `ctl_per_adv` and the
others); the build writes them as `noble_controller_config.CTL_LINKS` and
the like, and a feature whose count is `0` is out of the image and answers
its commands with Unknown HCI Command.  `novo config explain` prints the
storage the keys imply.  `configs/` holds the profiles this package's tests
run under.

The Host (`orbit/ble`) and a chip package depend on this package; it does
not depend on the Host, so an image that holds only a Controller carries no
Host code.  `docs/controller.md` describes the modules, the configuration
and the seams.

## Install, build and test

```sh
novo pkg add noble-controller
```

adds the package to the `[dependencies]` table of the consumer's `novo.toml`.  In a checkout of the package:

```sh
novo build
novo test
```

`novo build` type-checks and effect-checks every module under `src/`; the package is a library and writes no binary.
`novo test` runs the suites under `tests/`: one for each module that holds logic (`tests/<module>_tests.nv`, for
example `novo test tests/ll_scan_tests.nv`), and the suites that drive the Controller through HCI against a scripted
radio (`tests/ctl_*_tests.nv`, for example `novo test tests/ctl_air_tests.nv`).  A suite that needs a profile takes it
with `--config configs/ctl_iso.toml`.  The tests are not part of the published package.
