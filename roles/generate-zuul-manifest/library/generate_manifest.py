# Copyright 2019 Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import json
import logging
import mimetypes
import os
import stat
import sys

from ansible.module_utils.basic import AnsibleModule


if not mimetypes.inited:
    # We don't want to reinit and override any previously added types.
    mimetypes.init()


def path_in_tree(root, path):
    full_path = os.path.realpath(os.path.abspath(
        os.path.expanduser(path)))
    if not full_path.startswith(root):
        logging.debug("Skipping path outside root: %s" % (path,))
        return False
    return True


def _get_file_info(path):
    try:
        st = os.stat(path)
    except OSError:
        return 0, 0

    return st[stat.ST_MTIME], st[stat.ST_SIZE]


def walk(root, original_root=None):
    if original_root is None:
        original_root = root
    logging.debug("Walk: %s", root)
    data = []
    dirs = []
    files = []
    for e in os.listdir(root):
        if os.path.isdir(os.path.join(root, e)):
            if not os.path.islink(os.path.join(root, e)):
                dirs.append(e)
        else:
            files.append(e)
    for d in sorted(dirs):
        logging.debug("Directory: %s", d)
        path = os.path.join(root, d)
        if not path_in_tree(original_root, path):
            continue
        data.append(dict(name=d,
                         mimetype='application/directory',
                         encoding=None,
                         children=walk(os.path.join(root, d), original_root)))
    for f in sorted(files):
        logging.debug("File: %s", f)
        path = os.path.join(root, f)
        if not path_in_tree(original_root, path):
            continue
        mime_guess, encoding = mimetypes.guess_type(path)
        if not mime_guess:
            mime_guess = 'text/plain'
        last_modified, size = _get_file_info(path)
        if not last_modified and not size:
            continue
        data.append(dict(name=f,
                         mimetype=mime_guess,
                         encoding=encoding,
                         last_modified=last_modified,
                         size=size))
    return data


def run(root_path, output, index_links):
    data = walk(root_path, root_path)
    with open(output, 'w') as f:
        f.write(json.dumps({'tree': data,
                            'index_links': index_links}))


def ansible_main():
    module = AnsibleModule(
        argument_spec=dict(
            root=dict(type='path'),
            output=dict(type='path'),
            index_links=dict(type='bool', default=False),
        )
    )

    p = module.params
    run(p.get('root'), p.get('output'), p.get('index_links'))

    module.exit_json(changed=True)


def cli_main():
    parser = argparse.ArgumentParser(
        description="Generate a Zuul file manifest"
    )
    parser.add_argument('--verbose', action='store_true',
                        help='show debug information')
    parser.add_argument('root',
                        help='Root of upload directory')
    parser.add_argument('output',
                        help='Output file path')
    parser.add_argument('index_links', action='store_true',
                        help='Link to index.html instead of dirs')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    run(args.root, args.output, args.index_links)


if __name__ == '__main__':
    # The zip/ansible/modules check is required for Ansible 5 because
    # stdin may be a tty, but does not work in ansible 2.8.  The tty
    # check works on versions 2.8, 2.9, and 6.
    if ('.zip/ansible/modules' in sys.argv[0] or not sys.stdin.isatty()):
        ansible_main()
    else:
        cli_main()
