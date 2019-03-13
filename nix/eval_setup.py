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
parser.add_argument('--data')
args = parser.parse_args()

# Based on https://gist.github.com/shlevy/315d6b686065b31a0962d6e879cc0e32
setuptools.distutils.core._setup_stop_after = 'config'
with (getattr(tokenize, 'open', open))(args.setup_file) as setup_py:
    # Taken from from pip
    exec(compile(''.join(setup_py), __file__, 'exec'))
    cfg = setuptools.distutils.core._setup_distribution

metadata = {}
for key in ('name', 'version', 'url', 'download_url', 'project_urls', 'author',
            'author_email', 'maintainer', 'maintainer_email', 'classifiers',
            'license', 'description', 'long_description', 'keywords',
            'platforms', 'provides', 'requires', 'obsoletes'):
    value = getattr(cfg.metadata, key)
    if value or value is False:
        metadata[key] = to_value(value)

options = {}
for key in ('zip_safe', 'setup_requires', 'install_requires', 'extras_require',
            'python_requires', 'entry_points', 'use_2to3', 'use_2to3_fixers',
            'use_2to3_exclude_fixers', 'convert_2to3_doctests', 'scripts',
            'eager_resources', 'dependency_links', 'tests_require',
            'include_package_data', 'packages', 'package_dir', 'package_data',
            'exclude_package_data', 'namespace_packages', 'py_modules',
            'data_files'):
    value = getattr(cfg, key)
    if value or value is False:
        options[key] = to_value(value)

data = json.loads(args.data)
data['metadata'] = metadata
data['options'] = options
print(json.dumps(data))
