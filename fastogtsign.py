#!/usr/bin/env python3

'''
Code-signs all nested binaries inside an app bundle (excluding the app itself).
'''

import os, sys, re
import subprocess as sp
from base import system_info

SIGN_EXTENSIONS = ['.so', '.dylib']  # extension-less binaries are auto-included
CODE_SIGN_OPTS = ['--verbose', '--force', '--sign']


def is_translations(path):
    ext = os.path.splitext(path)[1]
    return ext == '.qm'


def is_probably_binary(path):
    ext = os.path.splitext(path)[1]
    if ext in SIGN_EXTENSIONS:
        return True
    return (len(ext) == 0) and os.access(path, os.X_OK) and not os.path.islink(path)


def is_definitely_binary(path):
    return 'Mach-O' in sp.check_output(['file', '--brief', path])


def get_signing_path(path):
    m = re.match('(.*/(.*)\.framework)/Versions/./(.*)', path)
    if m and (m.lastindex == 3) and m.group(2) == m.group(3):
        # This is the main binary of a framework. Sign the framework version instead.
        path = m.group(1)
    m = re.match('.*/(.*)\.app/Contents/MacOS/(.*)', path)
    if m and (m.lastindex == 2) and m.group(1) == m.group(2):
        # This is the main binary of the app bundle. Exclude it.
        path = None
    return path


def get_signable_binaries(path):
    all_files = [os.path.join(root, fn) for root, dirs, names in os.walk(path) for fn in names]
    trans = filter(is_translations, all_files)
    bins = filter(is_probably_binary, all_files)
    bins = filter(is_definitely_binary, bins)
    need_to_sign = [bins, trans]
    return sorted(filter(None, map(get_signing_path, need_to_sign)), reverse=True)


def code_sign_nested_macosx(identity, path, dryrun):
    signables = get_signable_binaries(path)
    if len(signables) == 0:
        print("No signable binaries found.")
        return False
    cmd = sp.check_output if not dryrun else lambda x: ' '.join(x)
    try:
        for bin in signables:
            print(cmd(['codesign'] + CODE_SIGN_OPTS + [identity, bin]))
    except sp.CalledProcessError:
        print('Code signing failed.')
        exit(1)
    print('%s successfully complete.' % ('Code signing' if not dryrun else 'Dry run'))


def main():
    if (len(sys.argv) != 4) or (sys.argv[1] not in ('sign', 'list')):
        print('Usage: %s sign/list signing_identity app_path' % os.path.basename(__file__))
        exit(1)
    cs_identity, app_path = sys.argv[2:]
    os_name = system_info.get_os()
    if os_name == 'macosx':
        code_sign_nested_macosx(cs_identity, app_path, dryrun=(sys.argv[1] == 'list'))
    else:
        print('Please implement code sign for: %s' % os_name)


if __name__ == '__main__':
    main()
