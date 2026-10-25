# iMac Radeon panel source patcher

For this iMac10,1: Radeon HD 4670, PCI 1002:9488, Apple subsystem
106b:00b6. Requires Python 3.9+ and GNU patch. No Python packages required.

This packages the existing experimental patch from ../imac-radeon-fix.
It changes the Radeon driver's RAM copy of the ATOM LCD_Info table, conditional
on the matching PCI IDs, 1920x1080 at 138500 kHz, table revision 1.2,
original clock 108000 kHz, and original LVDS flags 0x4d. It sets the table
clock to 138500 kHz and ORs the flags with 0x12 (RGB888/FPDI).
It does not flash a ROM or modify /lib/firmware microcode files.

The earlier build.log records successful compilation on Ubuntu kernel
6.14.0-37. Display correctness is NOT established by that log. This tool's
compatibility check verifies patch application, not C API compatibility or
hardware behavior. Future kernels may need manual porting. The patch remains
experimental; it is not a general Radeon repair tool.

## Use in a distro kernel build

Keep this directory together; patcher.py reads panel.patch beside itself.
Run as your normal user on a writable copy of your distro's Linux sources:

```sh
python3 patcher.py detect
python3 patcher.py check /path/to/linux-source
python3 patcher.py apply /path/to/linux-source
# Build and package the kernel using your distro's kernel packaging process.
# Enable CONFIG_DRM_RADEON=y or m and retain the distro's Radeon firmware.
```

Apply after the distro's other source patches and before kernel compilation.
Cross-building is supported: the build host need not be this iMac. The runtime
PCI and panel guards live in the patch. Application accepts exact context
with line offsets but no fuzzy matching. Incompatible layouts fail for review.
Repeated application makes no changes. The pre-existing source tree in
../imac-radeon-fix already contains this experiment.

For CI, `check` and `apply` return zero on compatible or already-patched trees,
and nonzero on errors. The tool neither downloads sources nor builds, installs,
signs, or loads modules. It does not change boot parameters. Kernel modules
need the matching configuration and build artifacts; see the upstream guide:
https://kernel.org/doc/html/next/kbuild/modules.html
Use your distro's kernel packaging and signing process for deployment.

## Undo and recovery

```sh
python3 patcher.py undo /path/to/linux-source
```

Undo restores the adjacent .imac-radeon-original backup only when both the
backup and current source match their recorded SHA-256 checksums. It refuses
to overwrite subsequent edits. Undo is available for changes made by this
tool, not pre-existing patches. Keep the adjacent backup and state files until
finished; exclude them from distro source packages. Run one patcher process
per tree and do not edit files concurrently.

Source undo does not replace an installed kernel. Retain a known-working
kernel and boot entry when testing the new build. After boot, inspect the
kernel log for `iMac LVDS test` and check panel colors, resolution, suspend,
and external outputs. The message only proves the quirk executed, not that
it fixed the display. No hardware validation was performed by this tool.
