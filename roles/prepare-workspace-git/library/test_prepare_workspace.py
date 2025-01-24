# Copyright 2024 Acme Gating, LLC
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

import os
import pprint
import shutil

import testtools
import fixtures

from ..module_utils.zuul_jobs.workspace_utils import for_each_project, run
from .repo_prep import prep_one_project
from .repo_sync import sync_one_project
from .repo_update import update_one_project
from . import repo_sync


class TestPrepareWorkspace(testtools.TestCase):
    def _test_prepare_workspace(self, connection, cached):
        executor_root = self.useFixture(fixtures.TempDir()).path
        project_root = os.path.join(executor_root,
                                    'example.com/org/test-project')
        os.makedirs(project_root)
        try:
            run("git init .", cwd=project_root)
            run("git config --local user.email user@example.com",
                cwd=project_root)
            run("git config --local user.name username",
                cwd=project_root)
            with open(os.path.join(project_root, 'README'), 'w') as f:
                f.write('test')
            run("git add README", cwd=project_root)
            run("git commit -a -m init", cwd=project_root)
        except Exception as e:
            if hasattr(e, 'output'):
                msg = '%s : %s' % (str(e), e.output)
            else:
                msg = str(e)
            print(msg)
            raise

        if cached:
            cache_root = self.useFixture(fixtures.TempDir()).path
            shutil.copytree(executor_root, cache_root, dirs_exist_ok=True)
        else:
            cache_root = '/doesnotexist'

        work_root = self.useFixture(fixtures.TempDir()).path
        params = {
            "ansible_connection": connection,
            "ansible_host": "testhost",
            "ansible_port": 22,
            "ansible_user": "zuul",
            "cached_repos_root": cache_root,
            "executor_work_root": executor_root,
            "inventory_hostname": "testhost",
            "zuul_workspace_root": work_root,
            "zuul_projects": {
                "example.com/org/test-project": {
                    "canonical_name": "example.com/org/test-project",
                    "checkout": "master",
                    "required": False,
                    "src_dir": "example.com/org/test-project"
                },
            },
            "zuul_resources": {
                "testhost": {
                    "context": "testcontext",
                    "namespace": "testnamespace",
                    "pod": "testpod",
                },
            },
        }

        # Verify the original behavior since we override it
        self.assertEqual('git+ssh://zuul@testhost:22/project',
                         repo_sync.get_ssh_dest(params, 'project'))

        self.assertEqual(
            '"ext::kubectl --context testcontext -n testnamespace '
            'exec -i testpod -- %S project"',
            repo_sync.get_k8s_dest(params, 'project'))

        def my_get_dest(args, dest):
            return dest

        def my_run(*args, **kw):
            env = kw.get('env', {})
            env.pop('GIT_ALLOW_PROTOCOL', None)
            return run(*args, **kw)

        # Override the destination to use a file instead
        self.patch(repo_sync, 'get_ssh_dest', my_get_dest)
        self.patch(repo_sync, 'get_k8s_dest', my_get_dest)
        self.patch(repo_sync, 'run', my_run)

        dest = os.path.join(work_root, 'example.com/org/test-project')

        output = {}
        ret = for_each_project(prep_one_project, params, output)
        pprint.pprint(output)
        self.assertTrue(ret)
        project_output = output['example.com/org/test-project']
        self.assertEqual(dest, project_output['dest'])
        if cached:
            self.assertEqual('cloned-from-cache',
                             project_output['initial_state'])
            self.assertTrue("Cloning into bare" in project_output['clone'])
        else:
            self.assertEqual('git-init', project_output['initial_state'])
            self.assertTrue("Initialized empty" in project_output['init'])
        self.assertTrue(project_output['elapsed'] > 0)

        output = {}
        ret = for_each_project(sync_one_project, params, output)
        pprint.pprint(output)
        self.assertTrue(ret)
        project_output = output['example.com/org/test-project']
        self.assertEqual(dest, project_output['dest'])
        self.assertEqual(1, project_output['attempts'])
        self.assertEqual('', project_output['push'])

        output = {}
        ret = for_each_project(update_one_project, params, output)
        pprint.pprint(output)
        self.assertTrue(ret)
        project_output = output['example.com/org/test-project']
        self.assertEqual(dest, project_output['dest'])
        head = run("git rev-parse HEAD", cwd=dest,
                   ).stdout.decode('utf8').strip()
        self.assertEqual('%s init' % (head,), project_output['HEAD'])
        self.assertTrue(project_output['elapsed'] > 0)

    def test_prepare_workspace_ssh_new(self):
        self._test_prepare_workspace('local', cached=False)

    def test_prepare_workspace_k8s_new(self):
        self._test_prepare_workspace('kubectl', cached=False)

    def test_prepare_workspace_ssh_cached(self):
        self._test_prepare_workspace('local', cached=True)

    def test_prepare_workspace_k8s_cached(self):
        self._test_prepare_workspace('kubectl', cached=True)
