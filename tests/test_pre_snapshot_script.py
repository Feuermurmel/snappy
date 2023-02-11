import json
import shlex

from conftest import get_mount_point, get_snapshots


def test_script(snappy_command, mocked_config_file, temp_filesystem):
    file_path = get_mount_point(temp_filesystem) / 'foo bar'
    script = f'echo hello > {shlex.quote(str(file_path))}'

    mocked_config_file.write_text(
        f'[[snapshot]]\n'
        f'datasets = ["{temp_filesystem}"]\n'
        f'pre_snapshot_script = {json.dumps(script)}\n')

    snappy_command('--auto')

    assert file_path.read_text() == 'hello\n'


def test_script_failure(
        snappy_command, mocked_config_file, temp_filesystem,
        fails_with_message):
    mocked_config_file.write_text(
        f'[[snapshot]]\n'
        f'datasets = ["{temp_filesystem}"]\n'
        f'pre_snapshot_script = "exit 5"')

    with fails_with_message('failed with exit code 5'):
        snappy_command('--auto')

    # No snapshots should be taken.
    assert not get_snapshots(temp_filesystem)
