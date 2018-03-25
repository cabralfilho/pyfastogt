#!/usr/bin/env python

'''
Code-signs all nested binaries inside an app bundle (excluding the app itself).
'''

import os, sys, re
import subprocess as sp


def main():
    if (len(sys.argv) != 4) or (sys.argv[1] not in ('sign', 'list')):
        print
        'Usage: %s sign/list signing_identity app_path' % os.path.basename(__file__)
        exit(1)
    cs_identity, app_path = sys.argv[2:]


if __name__ == '__main__':
    main()
