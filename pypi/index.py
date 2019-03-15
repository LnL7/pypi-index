"""
Generate a metadata index for python packages.
"""
__all__ = ('main',)

import argparse
import json
import os
import re
import subprocess
import sys

import pypi
from distlib.locators import SimpleScrapingLocator, normalize_name

pypi_exprs = os.path.abspath(os.path.join(__file__, '..', '..', 'nix'))


def build_nix_expression(path, *args, **kwargs):
    argv = ['nix-build', '--no-out-link', path,
            '-I', 'pypi={}'.format(pypi_exprs)]
    argv.extend(args)
    for name, value in kwargs.items():
        argv.extend(['--argstr', name, value])
    output = subprocess.check_output(argv)
    return output.decode('utf-8')


def digest_sort_key(item):
    url, (digest_algo, digest) = item
    return {'zip': 1, 'whl': 2}.get(url.rpartition('.')[2], 0)


def locate_digests(loc, pkg):
    dist = loc.locate(pkg)
    if dist:
        digests = sorted(dist.digests.items(), key=digest_sort_key)
        url, (digest_algo, digest) = digests[0]
        return {'name': normalize_name(dist.name),
                'version': dist.version,
                'fetchurl': {'url': url, digest_algo: digest}}
    else:
        raise SystemExit('error: failed to locate package')


def eval_queries(inputs):
    stdout = build_nix_expression('<pypi/setup.nix>',
                                  inputs=json.dumps(inputs))
    for out in stdout.splitlines():
        yield out


def query_command(args):
    pkgs = args.package
    loc = SimpleScrapingLocator(args.index_url, scheme='legacy')
    if '-' in pkgs:
        pkgs.remove('-')
        pkgs.extend(json.load(sys.stdin))
    for pkg in pkgs:
        query = locate_digests(loc, pkg)
        print(json.dumps(query))


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
        if nix_build_inputs:
            print('       buildInputs = [ %s ];' %
                  ' '.join(set(nix_build_inputs)))
        if nix_propagated_build_inputs:
            print('       propagatedBuildInputs = [ %s ];' %
                  ' '.join(set(nix_propagated_build_inputs)))
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
