"""
Generate a metadata index for python packages.
"""
__all__ = ('main',)

import argparse
import json
import os
import subprocess
import sys

import pypi
from distlib.locators import SimpleScrapingLocator

pypi_exprs = os.path.abspath(os.path.join(__file__, '..', '..', 'nix'))


def build_nix_expression(path, *args, **kwargs):
    argv = ['nix-build', '--no-out-link', path, '-I', 'pypi={}'.format(pypi_exprs)]
    argv.extend(args)
    for name, value in kwargs.items():
        argv.extend(['--arg', name, value])
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
        return {'name': dist.name,
                'version': dist.version,
                'fetchurl': {'url': url, digest_algo: digest}}
    else:
        raise SystemExit('error: failed to locate package')


def eval_queries(files):
    files_expr = '[' + ' '.join(files) + ']'
    stdout = build_nix_expression('<pypi/setup.nix>', files=files_expr)
    for out in stdout.splitlines():
        yield out


def query_command(args):
    index_url, pkgs = args.index_url, args.package
    loc = SimpleScrapingLocator(index_url, scheme='legacy')
    if '-' in pkgs:
        pkgs.remove('-')
        pkgs.extend(sys.stdin.readlines())
    for pkg in pkgs:
        query = locate_digests(loc, pkg)
        print(json.dumps(query))


def eval_command(args):
    files = sum(args.file, [])
    for out in eval_queries(files):
        with open(out) as f:
            print(f.read())


parser = argparse.ArgumentParser(prog='pypi-index')
subparsers = parser.add_subparsers()

VERSION = '%(prog)s ' + pypi.__version__
parser.add_argument('--version', action='version', version=VERSION)
parser.set_defaults(handler=lambda args: parser.print_help())

query_parser = subparsers.add_parser('query')
query_parser.set_defaults(handler=query_command)
query_parser.add_argument('package', nargs='+',
                         help='package(s) to query, if package is a single dash lines '
                              'will be read from standard input')
query_parser.add_argument('-i', '--index-url', default='https://pypi.org/simple',
                          help='url of python package index to query')

eval_parser = subparsers.add_parser('eval')
eval_parser.set_defaults(handler=eval_command)
eval_parser.add_argument('-f', '--file', nargs='+', action='append',
                        help='file(s) with package query metadata to evaluate')
eval_parser.add_argument('--eval-backend', default='nix', choices=('nix',))


def main():
    args = parser.parse_args()
    args.handler(args)


if __name__ == '__main__':
    main()
