from datetime import datetime

from snappy import parse_keep_spec, Dataset
from snappy.snapshots import find_expired_snapshots, _timestamp_format
from snappy.zfs import Snapshot, SnapshotInfo


snapshot_timestamps = [
    '2023-02-12 23:59',
    '2023-02-13 01:00',
    '2023-02-16 02:00',
    '2023-02-18 01:00',
    '2023-02-20 01:00',
    '2023-02-25 11:00',
    '2023-02-25 12:00',
    '2023-02-26 13:02',
    '2023-02-26 13:03',
    '2023-02-27 15:03',
    '2023-02-27 15:04',
    '2023-02-27 15:05']


def snapshots_from_timestamps(timestamps: list[str]) -> list[SnapshotInfo]:
    res: list[SnapshotInfo] = []

    for i, t in enumerate(timestamps):
        name = f'foo-{datetime.fromisoformat(t):{_timestamp_format}}'

        res.append(SnapshotInfo(Snapshot(Dataset('dummy'), name), i, i))

    return res


def check_kept_snapshots(
        keep_spec_strs: list[str], expected_selected_snapshot_names: list[str]):
    keep_specs = [parse_keep_spec(i) for i in keep_spec_strs]

    snapshots = snapshots_from_timestamps(snapshot_timestamps)
    expected_selected_snapshots = {
        i.snapshot
        for i in snapshots_from_timestamps(expected_selected_snapshot_names)}

    selected_snapshots = \
        {i.snapshot for i in snapshots_from_timestamps(snapshot_timestamps)} \
        - find_expired_snapshots(snapshots, keep_specs, 'foo')

    assert selected_snapshots == expected_selected_snapshots


def test_keep_most_recent():
    check_kept_snapshots(
        ['3'],
        ['2023-02-27 15:03', '2023-02-27 15:04',  '2023-02-27 15:05'])


def test_keep_hourly():
    check_kept_snapshots(
        ['1h:3'],
        ['2023-02-25 12:00', '2023-02-26 13:02',  '2023-02-27 15:03'])


def test_keep_2_daily():
    check_kept_snapshots(
        ['2d:3'],
        ['2023-02-20 01:00', '2023-02-25 11:00',  '2023-02-27 15:03'])


def test_keep_weekly():
    check_kept_snapshots(
        ['1w'],
        ['2023-02-12 23:59', '2023-02-13 01:00',  '2023-02-20 01:00',
         '2023-02-27 15:03'])


def test_keep_combined():
    check_kept_snapshots(
        ['1h:2', '1w'],
        ['2023-02-12 23:59', '2023-02-13 01:00', '2023-02-20 01:00',
         '2023-02-26 13:02', '2023-02-27 15:03'])
