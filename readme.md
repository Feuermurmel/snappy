# snappy - Create and prune ZFS snapshots

```
usage: snappy [-h] [-r] [-k KEEP SPECIFICATION] [-p] [--auto]
              [--config CONFIG_PATH]
              [DATASETS ...]

Create and/or prune snapshots on ZFS filesystems.

positional arguments:
  DATASETS              Datasets on which to create (and prune) snapshots.

options:
  -h, --help            show this help message and exit
  -r, --recursive       Create and prune snapshots recursively on the
                        specified datasets.
  -k KEEP SPECIFICATION, --keep KEEP SPECIFICATION
                        Prune old snapshots after creating a new one. This
                        option can be given multiple times to keep additional
                        snapshots in different time intervals.
  -p, --prune-only      Disables creating snapshots. Requires --keep.
  --auto                Run the snapshot and prune actions specified in the
                        configuration file instead of on the command line.
  --config CONFIG_PATH  Path to the configuration file to use. Requires
                        --auto. Defaults to `/etc/snappy/snappy.toml'.

KEEP SPECIFICATION

Either a number or a TIME INTERVAL. When a number is given, it specifies to
keep that many most recent snapshots.

If a time interval is given, it specifies to keep one snapshot per that
interval. The interval can be followed by a `:' and a number, which specifies
to keep only that many most recent snapshots taken in that interval.

TIME INTERVAL

A number followed by one of the time units `s', `m', `h', `d', or `w',
specifying an interval of that many seconds, minutes, hours, days, or weeks
respectively.
```


## Development Setup

```
make venv
```
