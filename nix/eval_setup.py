#!/usr/bin/env python
import argparse
import json
import tokenize

import setuptools


def add_install_requires(extras, requires):
    for key, values in extras.items():
        _, _, expr = key.partition(':')
        if expr:
            for elem in values:
                requires.append('{}; {}'.format(elem, expr))


def to_value(x):
    return list(x) if isinstance(x, set) else x


parser = argparse.ArgumentParser(prog='setup')
parser.add_argument('setup_file', nargs='?', default='setup.py')
parser.add_argument('--name')
parser.add_argument('--version')
args = parser.parse_args()

# Based on https://gist.github.com/shlevy/315d6b686065b31a0962d6e879cc0e32
setuptools.distutils.core._setup_stop_after = 'config'
with (getattr(tokenize, 'open', open))(args.setup_file) as setup_py:
    # Taken from from pip
    exec(compile(''.join(setup_py), __file__, 'exec'))
    cfg = setuptools.distutils.core._setup_distribution

metadata = {k: to_value(v) for k, v in cfg.metadata.__dict__.items() if v}
add_install_requires(cfg.extras_require, cfg.install_requires)
options = {
    'packages': cfg.packages or [],
    'install_requires': cfg.install_requires or [],
    'setup_requires': cfg.setup_requires or [],
    'tests_require': cfg.tests_require or [],
    'entry_points': cfg.entry_points or {}
}
if cfg.zip_safe is not None:
    options['zip_safe'] = cfg.zip_safe

name = args.name or metadata['name']
version = args.version or metadata['version']

data = {'name': name, 'version': version,
        'metadata':  metadata, 'options': options}
print(json.dumps(data))
