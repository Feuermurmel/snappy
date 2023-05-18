# TODO: Test multiple datasets without send base


def test_invalid_argument_combinations(snappy_command, fails_with_message):
    with fails_with_message('DATASETS is required unless --auto is given'):
        snappy_command('')

    with fails_with_message('--no-snapshot requires either --keep or --send-to'):
        snappy_command('-S foo')

    with fails_with_message('--send-base requires --send-to'):
        snappy_command('-b x foo')

    with fails_with_message('--auto conflicts with'):
        snappy_command('--auto -p x')

    with fails_with_message(
            '--send-to requires --send-base if more than one dataset is '
            'specified'):
        snappy_command('fishtank/a fishtank/b -s watertank')


def test_invalid_keep_spec(snappy_command, fails_with_message):
    with fails_with_message('argument -k/--keep: Missing count or interval.'):
        snappy_command('-k w')
