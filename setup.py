import setuptools


setuptools.setup(
    name='snappy',
    version='1.0.0',
    packages=['snappy'],
    entry_points=dict(
        console_scripts=[
            "snappy = snappy:script_main"]),
    install_requires=[])
