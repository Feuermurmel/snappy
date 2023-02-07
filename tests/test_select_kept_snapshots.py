from datetime import datetime

from snappy import parse_keep_spec
from snappy.snapshots import SnapshotInfo, select_snapshots_to_keep


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


snapshots = [
    SnapshotInfo(i, datetime.fromisoformat(i))
    for i in snapshot_timestamps]


def check_kept_snapshots(
        keep_spec_strs: list[str], expected_selected_snapshots: list[str]):
    keep_specs = [parse_keep_spec(i) for i in keep_spec_strs]

    expected_selected_snapshot_timestamps = {
        datetime.fromisoformat(i)
        for i in expected_selected_snapshots}

    selected_snapshots = select_snapshots_to_keep(snapshots, keep_specs)

    assert {i.timestamp for i in selected_snapshots} \
           == expected_selected_snapshot_timestamps


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
