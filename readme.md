# snappy - Create and prune ZFS snapshots

```
usage: snappy [-h] [-r] [-e EXCLUDE] [-p PREFIX] [-S] [-k KEEP_SPECIFICATIONS]
              [-s TARGET] [-b SEND_BASE] [--auto] [--config CONFIG_PATH]
              [DATASETS ...]

Create and/or prune snapshots on ZFS filesystems.

positional arguments:
  DATASETS              Datasets on which to create and prune snapshots.

options:
  -h, --help            show this help message and exit
  -r, --recursive       Include children of the specified datasets when
                        creating, sending, and/or pruning snapshots.
  -e EXCLUDE, --exclude EXCLUDE
                        Exclude a dataset and its children when enumerating
                        datasets recursively.
  -p PREFIX, --prefix PREFIX
                        Prefix of snapshot names of created and pruned
                        snapshots. Defaults to `snappy'.
  -S, --no-snapshot     Disables creating snapshots. Instead, only prune
                        and/or send snapshots.

pruning:
  -k KEEP_SPECIFICATIONS, --keep KEEP_SPECIFICATIONS
                        Prune snapshots according to this list of keep
                        specifications.
                        See https://github.com/Feuermurmel/snappy#pruning.

sending snapshots:
  -s TARGET, --send-to TARGET
                        Send the snapshots of the DATASETS into child
                        filesystem of this target filesystem. If specified,
                        pruning will happen on the target datasets instead of
                        the source datasets.
  -b SEND_BASE, --send-base SEND_BASE
                        The path prefix that is stripped from each of DATASETS
                        and replaced with TARGET when sending snapshots to
                        construct the names of the destination datasets.
                        Without this option, only a single source dataset can
                        be sent at a time, which is sent directly to TARGET.

running from config file:
  --auto                Run the snapshot and prune actions specified in the
                        configuration file instead of on the command line.
  --config CONFIG_PATH  Path to the configuration file to use. Requires
                        --auto. Defaults to `/etc/snappy/snappy.toml'.
```


## Pruning

`snappy` can be instructed to prune snapshots, to select a set of existing snapshots and destroy the rest. This can happen after creating a new snapshot and/or sending snapshots to a target dataset, as well as on its own.

The set of snapshots to keep is specified using `--keep`, followed by a comma-separated list of keep specifications:

```
snappy -k 1d:7,1w:10 fishtank
```

This would keep daily snapshots for a week and weekly snapshots for 10 weeks. As a special case, the most recent snapshot taken is always kept. This is to prevent losing last snapshot that was sent from another dataset, which is necessary to continue with incremental replication.

Each keep specification is either a count like `5` or a time interval like `1w`, optionally followed by a count, like `1w:10`. A count `n` will cause the most recent `n` snapshots to be kept. A time interval `i:n` will cause the earliest snapshot for each interval `i` to be kept, up `n` snapshots, if given.

A time interval is specified as an integer followed by one of the units `s`, `m`, `h`, `d`, or `w`, specifying an interval of that many seconds, minutes, hours, days, or weeks respectively.

A combination of count and interval specifications can be given. If multiple specifications are given, each will select a subset of the existing snapshots and the union of all selected snapshots will be kept, while the others are destroyed.


## Development Setup

```
make venv
```
