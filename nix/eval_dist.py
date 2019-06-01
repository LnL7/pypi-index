#!/usr/bin/env python
import argparse

import glob
import json
import sys
from distlib.version import parse_requirement
from distlib.wheel import Wheel

parser = argparse.ArgumentParser(prog='dist')
parser.add_argument('output')
parser.add_argument('--data')
args = parser.parse_args()

wheels = glob.glob('*.whl')
if len(wheels) != 1:
    print('error: no *.whl found', file=sys.stderr)
    exit(1)

whl = Wheel(wheels[0])
meta = whl.metadata.todict()

aliases = {'url': 'home_page', 'description': 'summary'}

metadata = {}
for key in ('name', 'version', 'url', 'download_url', 'project_urls', 'author',
            'author_email', 'maintainer', 'maintainer_email', 'classifiers',
            'license', 'description', 'long_description', 'keywords',
            'platforms', 'provides', 'requires', 'obsoletes'):
    value = meta.get(key, None)
    if value is None and key in aliases:
        value = meta.get(aliases[key], None)
    if value or value is False:
        metadata[key] = value

options = {}
requires = [parse_requirement(x) for x in whl.metadata.run_requires]
options['install_requires'] = [x.requirement.replace(' ', '')
                               for x in requires if not x.marker]

def from_marker(marker):
    if isinstance(marker, str):
        return None, marker
    elif marker['lhs'] == 'extra':
        return marker['rhs'].replace('\'', ''), None
    else:
        lextra, lhs = from_marker(marker['lhs'])
        rextra, rhs = from_marker(marker['rhs'])
        if lextra:
            return lextra, rhs
        elif rextra:
            return rextra, lhs
        else:
            return '', ' '.join([lhs, marker['op'], rhs])


extras = {}
for req in (x for x in requires if x.marker):
    key = ':'.join(x for x in from_marker(req.marker) if x is not None)
    extras[key] = extras.get(key, [])
    extras[key].append(req.requirement.replace(' ', ''))
options['extras_require'] = extras

data = json.loads(args.data)
data['metadata'] = metadata
data['options'] = options
with open(args.output, 'w') as f:
    json.dump(data, f)
