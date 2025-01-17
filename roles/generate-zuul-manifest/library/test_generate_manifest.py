# Copyright (C) 2019 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import stat
import testtools
import fixtures

from .generate_manifest import _get_file_info
from .generate_manifest import walk


FIXTURE_DIR = os.path.join(os.path.dirname(__file__),
                           'test-fixtures')


class SymlinkFixture(fixtures.Fixture):
    links = [
        ('bad_symlink', '/etc'),
        ('bad_symlink_file', '/etc/issue'),
        ('good_symlink', 'controller'),
        ('recursive_symlink', '.'),
        ('symlink_file', 'job-output.json'),
        ('symlink_loop_a', 'symlink_loop'),
        ('symlink_loop/symlink_loop_b', '..'),
    ]

    def _setUp(self):
        for (src, target) in self.links:
            path = os.path.join(FIXTURE_DIR, 'links', src)
            os.symlink(target, path)
            self.addCleanup(os.unlink, path)


class TestFileList(testtools.TestCase):

    def flatten(self, result, out=None, path=''):
        if out is None:
            out = []
        dirs = []
        for x in result:
            x['_relative_path'] = os.path.join(path, x['name'])
            out.append(x)
            if 'children' in x:
                dirs.append(x)
        for x in dirs:
            self.flatten(x['children'], out, x['_relative_path'])
            x.pop('children')
        return out

    def assert_files(self, root, result, files):
        self.assertEqual(len(result), len(files))
        for expected, received in zip(files, result):
            self.assertEqual(expected[0], received['_relative_path'])
            if expected[0] and expected[0][-1] == '/':
                efilename = os.path.split(
                    os.path.dirname(expected[0]))[1] + '/'
            else:
                efilename = os.path.split(expected[0])[1]
            self.assertEqual(efilename, received['name'])
            full_path = os.path.join(root, received['_relative_path'])
            if received['mimetype'] == 'application/directory':
                self.assertTrue(os.path.isdir(full_path))
            else:
                self.assertTrue(os.path.isfile(full_path))
            self.assertEqual(expected[1], received['mimetype'])
            self.assertEqual(expected[2], received['encoding'])

    def find_file(self, file_list, path):
        for f in file_list:
            if f.relative_path == path:
                return f

    def test_single_dir(self):
        '''Test a single directory with a trailing slash'''

        root = os.path.join(FIXTURE_DIR, 'logs')
        fl = walk(root)
        self.assert_files(root, self.flatten(fl), [
            ('controller', 'application/directory', None),
            ('zuul-info', 'application/directory', None),
            ('job-output.json', 'application/json', None),
            ('controller/subdir', 'application/directory', None),
            ('controller/compressed.gz', 'text/plain', 'gzip'),
            ('controller/cpu-load.svg', 'image/svg+xml', None),
            ('controller/journal.xz', 'text/plain', 'xz'),
            ('controller/service_log.txt', 'text/plain', None),
            ('controller/syslog', 'text/plain', None),
            ('controller/subdir/subdir.txt', 'text/plain', None),
            ('zuul-info/inventory.yaml', 'text/plain', None),
            ('zuul-info/zuul-info.controller.txt', 'text/plain', None),
        ])

    def test_symlinks(self):
        '''Test symlinks'''
        self.useFixture(SymlinkFixture())
        root = os.path.join(FIXTURE_DIR, 'links')
        fl = walk(root)
        self.assert_files(root, self.flatten(fl), [
            ('controller', 'application/directory', None),
            ('symlink_loop', 'application/directory', None),
            ('job-output.json', 'application/json', None),
            ('symlink_file', 'text/plain', None),
            ('controller/service_log.txt', 'text/plain', None),
            ('symlink_loop/placeholder', 'text/plain', None),
        ])

    def test_get_file_info(self):
        '''Test files info'''
        path = os.path.join(FIXTURE_DIR, 'logs', 'job-output.json')
        last_modified, size = _get_file_info(path)

        self.assertEqual(os.stat(path)[stat.ST_MTIME], last_modified)
        self.assertEqual(16, size)

    def test_get_file_info_missing_file(self):
        '''Test files that go missing during a walk'''
        last_modified, size = _get_file_info('missing/file/that/we/cant/find')

        self.assertEqual(0, last_modified)
        self.assertEqual(0, size)
