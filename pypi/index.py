"""
Generate a metadata index for python packages.
"""
__all__ = ('main',)

import argparse
import glob
import itertools
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

import pypi
import requests
from distlib.locators import SimpleScrapingLocator, normalize_name

pypi_exprs = os.path.abspath(os.path.join(__file__, '..', '..', 'nix'))


def build_nix_expression(path, *args, **kwargs):
    try:
        for result in glob.glob('build/result*'):
            os.remove(result)
        argv = ['nix', 'build', '--option', 'keep-going', 'true',
                '-I', 'pypi={}'.format(pypi_exprs), '-f', path,
                '-o', 'build/result']
        argv.extend(args)
        for name, value in kwargs.items():
            argv.extend(['--argstr', name, value])
        subprocess.check_call(argv)
        return glob.glob('build/result*')
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)



def digest_sort_key(item):
    url, (digest_algo, digest) = item
    return {'zip': 1, 'whl': 2}.get(url.rpartition('.')[2], 0)


def digest_header_fallback(url):
    res = requests.head(url)
    sha256 = res.headers.get('X-Checksum-Sha256')
    if sha256:
        return 'sha256', sha256
    else:
        return None, None


def locate_digests(loc, pkg):
    pkg, _, _ = pkg.partition('#')
    dist = loc.locate(pkg)
    if dist:
        digests = iter(sorted(dist.digests.items(), key=digest_sort_key))
        try:
            url, (digest_algo, digest) = next(digests)
        except StopIteration:
            return None
        if digest_algo not in ('sha256', 'sha521'):
            digest_algo, digest = digest_header_fallback(url)
        if digest_algo:
            return {'name': normalize_name(dist.name),
                    'version': dist.version,
                    'fetchurl': {'url': url, digest_algo: digest}}
        else:
            raise SystemExit('error: failed to retrieve digest')
    else:
        raise SystemExit('error: failed to locate package')


def eval_queries(inputs):
    return build_nix_expression('<pypi/setup.nix>',
                                inputs=json.dumps(inputs))


def query_command(args):
    pkgs = args.package
    loc = SimpleScrapingLocator(args.index_url, scheme='legacy')
    if '-' in pkgs:
        pkgs.remove('-')
        pkgs.extend(json.load(sys.stdin))
    for pkg in pkgs:
        query = locate_digests(loc, pkg)
        if query:
            print(json.dumps(query))
        else:
            print('error: could not locate source for {}'.format(pkg), file=sys.stderr)


def eval_command(args):
    files = args.file
    inputs = []
    if '-' in files:
        files.remove('-')
        query = json.load(sys.stdin)
        inputs = query if isinstance(query, list) else [query]
    for path in files:
        with open(path) as f:
            inputs.append(json.load(f))

    for out in eval_queries(inputs):
        with open(out) as f:
            print(f.read())


def build_command(args):
    loc = SimpleScrapingLocator(args.index_url, scheme='legacy')

    iteration = itertools.count(1)
    index = defaultdict(dict)
    skip = set(args.blacklist)
    requires = [x for x in args.package]

    while requires:
        inputs = []
        for req in requires:
            data = locate_digests(loc, req)
            if data:
                inputs.append(data)
            else:
                print('error: could not locate source for {}'.format(req), file=sys.stderr)

        skip |= set(requires)
        requires = []
        for out in eval_queries(inputs):
            with open(out) as f:
                data = json.load(f)
                name, version = data['name'], data['version']
                index[name][version] = data
                requires.extend(data['options'].get('setup_requires', []))
                requires.extend(data['options'].get('install_requires', []))
                if args.tests:
                    requires.extend(data['options'].get('tests_require', []))

        if not args.recurse:
            break

        requires = [x for x in requires if x not in skip]

        n = sum(len(x) for x in index.values())
        i = next(iteration)
        print('[{:>2}/{:>2}] building index...'.format(n, i), file=sys.stderr)

    for name, versions in index.items():
        for version, data in versions.items():
            if args.print_requirements:
                print('{}=={}'.format(name, version))
            else:
                print(json.dumps(data))


def expr_command(args):
    files = args.file
    inputs = []
    if '-' in files:
        files.remove('-')
        query = json.load(sys.stdin)
        inputs = query if isinstance(query, list) else [query]
    for path in files:
        with open(path) as f:
            inputs.append(json.load(f))
    print('{ pkgs, lib, callPackage }:')
    print('{')
    for cfg in inputs:
        name, version = cfg['name'], cfg['version'].replace('.', '_')
        wheel = cfg['fetchurl']['url'].endswith('.whl')
        setup_requires = [re.split(r'[<=>!]', x)[0] for x in
                          cfg['options'].get('setup_requires', [])]
        install_requires = [re.split(r'[<=>!]', x)[0] for x in
                            cfg['options'].get('install_requires', [])]
        nix_build_inputs = args.add_build_input + setup_requires
        nix_propagated_build_inputs = args.add_propagated_build_input \
            + install_requires
        nix_inputs = ['buildPythonPackage', 'fetchurl'] \
            + nix_build_inputs + nix_propagated_build_inputs
        nix_description = cfg['metadata'].get('description')
        nix_license = {'MIT': 'mit'}.get(cfg['metadata'].get('license'))
        print('  %s_%s = callPackage' % (name, version))
        print('    ({ %s }:' % ', '.join(set(nix_inputs)))
        print('     buildPythonPackage rec {')
        print('       pname = "%s";' % cfg['metadata']['name'])
        print('       version = "%s";' % cfg['metadata']['version'])
        print('       src = fetchurl {')
        print('         url = "%s";' % cfg['fetchurl']['url'])
        print('         sha256 = "%s";' % cfg['fetchurl']['sha256'])
        print('       };')
        if wheel:
            print('       format = "wheel";')
        if nix_build_inputs:
            print('       buildInputs = [ %s ];' %
                  ' '.join(set(nix_build_inputs)))
        if nix_propagated_build_inputs:
            print('       propagatedBuildInputs = [ %s ];' %
                  ' '.join(set(nix_propagated_build_inputs)))
        print('       doCheck = false;')
        print('       meta = with lib; {')
        if nix_description:
            print('         description = "%s";' % nix_description)
        if nix_license:
            print('         license = licenses.%s;' % nix_license)
        print('       };')
        print('     }) { };')
    print('}')


parser = argparse.ArgumentParser(prog='pypi-index')
subparsers = parser.add_subparsers()

VERSION = '%(prog)s ' + pypi.__version__
parser.add_argument('--version', action='version', version=VERSION)
parser.set_defaults(handler=lambda args: parser.print_help())

query_parser = subparsers.add_parser('query')
query_parser.set_defaults(handler=query_command)
query_parser.add_argument('package', nargs='+',
                          help='package(s) to query, if package is a single '
                               'dash a json list will be read from '
                               'standard input')
query_parser.add_argument('-i', '--index-url',
                          default='https://pypi.org/simple',
                          help='url of python package index to query')

eval_parser = subparsers.add_parser('eval')
eval_parser.set_defaults(handler=eval_command)
eval_parser.add_argument('file', nargs='+',
                         help='file(s) with package query metadata to '
                              'evaluate, if file is a single dash a json list '
                              'will be read from standard input')
eval_parser.add_argument('--eval-backend', default='nix', choices=('nix',))

build_parser = subparsers.add_parser('build')
build_parser.set_defaults(handler=build_command)
build_parser.add_argument('package', nargs='+')
build_parser.add_argument('--recurse', default=True, action='store_true')
build_parser.add_argument('--no-recurse', dest='recurse', action='store_false')
build_parser.add_argument('--tests', default=True, action='store_true')
build_parser.add_argument('--no-tests', dest='tests', action='store_false')
build_parser.add_argument('--blacklist', default=[], action='append')
build_parser.add_argument('--print-requirements', action='store_true')
build_parser.add_argument('-i', '--index-url',
                          default='https://pypi.org/simple',
                          help='url of python package index to query')

expr_parser = subparsers.add_parser('expr')
expr_parser.set_defaults(handler=expr_command)
expr_parser.add_argument('file', nargs='+',
                         help='file(s) with package query metadata to '
                              'evaluate, if file is a single dash a json list '
                              'will be read from standard input')
expr_parser.add_argument('--add-build-input', default=[], action='append')
expr_parser.add_argument('--add-propagated-build-input', default=[], action='append')
expr_parser.add_argument('--output-type', default='nix', choices=('nix',))


def main():
    args = parser.parse_args()
    args.handler(args)


if __name__ == '__main__':
    main()
