def test_temp_fs(temp_filesystem):
    (temp_filesystem.path / 'file').touch()
