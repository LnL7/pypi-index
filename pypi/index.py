"""
Generate a metadata index for python packages.
"""
__all__ = ('main',)

import argparse
import json
import sys

import pypi
from distlib.locators import SimpleScrapingLocator


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


def query_command(args):
    index_url, pkgs = args.index_url, args.package
    loc = SimpleScrapingLocator(index_url, scheme='legacy')
    if '-' in pkgs:
        pkgs.remove('-')
        pkgs.extend(sys.stdin.readlines())
    for pkg in pkgs:
        query = locate_digests(loc, pkg)
        print(json.dumps(query))


parser = argparse.ArgumentParser(prog='pypi-index')
subparsers = parser.add_subparsers()

VERSION = '%(prog)s ' + pypi.__version__
parser.add_argument('--version', action='version', version=VERSION)
parser.set_defaults(handler=lambda args: parser.print_help())

query_parser = subparsers.add_parser('query')
query_parser.set_defaults(handler=query_command)
query_parser.add_argument('package', nargs='+',
                         help='list of package to query, if package is a single dash '
                              'lines will be read from standard input')
query_parser.add_argument('-i', '--index-url', default='https://pypi.org/simple',
                          help='url of python package index to query')


def main():
    args = parser.parse_args()
    args.handler(args)


if __name__ == '__main__':
    main()
