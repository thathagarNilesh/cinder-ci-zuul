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
import time

from ansible.module_utils.basic import AnsibleModule

try:
    # Ansible context
    from ansible.module_utils.zuul_jobs.workspace_utils import (
        run,
        for_each_project,
    )
except ImportError:
    # Test context
    from ..module_utils.zuul_jobs.workspace_utils import (
        run,
        for_each_project,
    )


def prep_one_project(args, project, output):
    start = time.monotonic()
    dest = "%s/%s" % (args['zuul_workspace_root'], project['src_dir'])
    output['dest'] = dest
    if not os.path.isdir(dest):
        cache = "%s/%s" % (args['cached_repos_root'],
                           project['canonical_name'])
        if os.path.isdir(cache):
            # We do a bare clone here first so that we skip creating a working
            # copy that will be overwritten later anyway.
            output['initial_state'] = 'cloned-from-cache'
            out = run("git clone --bare %s %s/.git" % (cache, dest))
            output['clone'] = out.stdout.decode('utf8').strip()
        else:
            output['initial_state'] = 'git-init'
            out = run("git init %s" % (dest,))
            output['init'] = out.stdout.decode('utf8').strip()
    else:
        output['initial_state'] = 'pre-existing'

    run("git config --local --bool core.bare false", cwd=dest)
    # Allow pushing to non-bare repo
    run("git config --local receive.denyCurrentBranch ignore", cwd=dest)
    # Allow deleting current branch
    run("git config --local receive.denyDeleteCurrent ignore", cwd=dest)
    run("git remote rm origin", cwd=dest, check=False)
    run("git remote add origin file:///dev/null", cwd=dest)
    end = time.monotonic()
    output['elapsed'] = end - start


def ansible_main():
    module = AnsibleModule(
        argument_spec=dict(
            cached_repos_root=dict(type='path'),
            executor_work_root=dict(type='path'),
            zuul_projects=dict(type='dict'),
            zuul_workspace_root=dict(type='path'),
        )
    )

    output = {}
    if for_each_project(prep_one_project, module.params, output):
        module.exit_json(changed=True, output=output)
    else:
        module.fail_json("Failure preparing repos", output=output)


if __name__ == '__main__':
    ansible_main()
