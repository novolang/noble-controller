# Changelog

Every published version, newest first. This file is on the publish
allow-list, so it travels with the package: it is the only thing a
consumer deciding whether to upgrade can read.

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
