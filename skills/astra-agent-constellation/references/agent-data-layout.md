# Agent host data: what lives where, and what may be deleted

An agent host accumulates four kinds of data, with different lifetimes. Mixing
them is how a rebuild loses a working environment — or how a backup silently
grows to hundreds of gigabytes of re-downloadable blobs.

## Categories

| Category | Examples | Lifetime | Backup |
|:--|:--|:--|:--|
| Model weights | GGUF/GGML files, embedding models | re-downloadable, large, often pinned by checksum | no — record the source and checksum instead |
| Container images and volumes | runtime images, named volumes with service state | images: re-pullable; volumes: real state | volumes only |
| Agent homes and runner state | per-agent home, session logs, workspaces | mixed: config is disposable, artefacts may not be | selectively |
| Toolchain caches | cargo/go/uv/pnpm stores used by builds the agent drives | rebuildable | no |

The rule that follows: **a backup is for what cannot be re-created.** Model
weights and layer caches can be re-created from a pinned source; a workspace
that holds work in progress cannot.

## Placement

Keep all four on the same large local filesystem, in sibling directories, so the
total footprint is visible in one place and one disk decision covers them:

```
<bigdisk>/models        weights
<bigdisk>/containers    image/volume storage for the container runtime
<bigdisk>/runner        agent runner state and workspaces
<bigdisk>/cache         toolchain caches (see linux-host-admin: toolchain caches)
```

Nothing here belongs on tmpfs, and nothing belongs inside a package-manager
store. Both mistakes produce the same late failure: the data is present while a
build runs and gone after a reboot.

## Agent home is not configuration

Per-agent homes accumulate generated files (installed tools, downloaded
runtimes, session caches) that make a rebuild *look* reproducible while
depending on hand-unpacked binaries. The configuration that matters — profiles,
skills, service units — belongs in version-controlled repositories; the home is
output, not source. When a home contains a hand-installed tool that a rebuild
needs, package it instead of backing up the directory.

## Retention checks

1. Before any "clean up disk" pass, measure per directory and classify each by
   the table above.
2. Delete model weights only when the pin (URL + checksum) is recorded
   somewhere restorable.
3. Volumes with service state are never deleted by a cache-pruning habit; they
   are deleted as a deliberate data decision.
4. Session logs and workspaces that hold unfinished work are the only agent-side
   data whose loss is not recoverable by re-downloading.
