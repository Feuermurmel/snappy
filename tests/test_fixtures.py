from conftest import get_mount_point


def test_temp_fs(temp_filesystem):
    mount_point = get_mount_point(temp_filesystem)

    (mount_point / 'file').touch()
