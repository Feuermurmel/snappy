from conftest import get_mount_point


def test_temp_fs(filesystem):
    mount_point = get_mount_point(filesystem)

    (mount_point / 'file').touch()
