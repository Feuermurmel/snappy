def test_invalid_argument_combinations(snappy_command, fails_with_message):
    with fails_with_message('DATASETS is required unless --auto is given'):
        snappy_command('')

    with fails_with_message('--no-snapshot requires --keep'):
        snappy_command('-S foo')

    with fails_with_message('--auto conflicts with'):
        snappy_command('--auto -p x')


def test_invalid_keep_spec(snappy_command, fails_with_message):
    with fails_with_message('argument -k/--keep: Missing count or interval.'):
        snappy_command('-k w')
