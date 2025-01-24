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


def get_ssh_dest(args, dest):
    return (
        "git+ssh://%s@%s:%s/%s" % (
            args['ansible_user'],
            args['ansible_host'],
            args['ansible_port'],
            dest)
    )


def get_k8s_dest(args, dest):
    resources = args['zuul_resources'][args['inventory_hostname']]
    return (
        "\"ext::kubectl --context %s -n %s exec -i %s -- %%S %s\"" % (
            resources['context'],
            resources['namespace'],
            resources['pod'],
            dest)
    )


def sync_one_project(args, project, output):
    cwd = "%s/%s" % (args['executor_work_root'], project['src_dir'])
    dest = "%s/%s" % (args['zuul_workspace_root'], project['src_dir'])
    output['src'] = cwd
    output['dest'] = dest
    env = os.environ.copy()
    env['GIT_ALLOW_PROTOCOL'] = 'ext:ssh'
    # We occasionally see git pushes in the middle of this loop fail then
    # subsequent pushes for other repos succeed. The entire loop ends up
    # failing because one of the pushes failed. Mitigate this by retrying
    # on failure.
    max_tries = 3
    start = time.monotonic()
    for count in range(max_tries):
        try:
            if args['ansible_connection'] == "kubectl":
                git_dest = get_k8s_dest(args, dest)
            else:
                git_dest = get_ssh_dest(args, dest)
            out = run("git push --quiet --mirror %s" % (git_dest,),
                      cwd=cwd, env=env)
            output['push'] = out.stdout.decode('utf8').strip()
            break
        except Exception:
            if count + 1 >= max_tries:
                raise
    end = time.monotonic()
    output['attempts'] = count + 1
    output['elapsed'] = end - start


def ansible_main():
    module = AnsibleModule(
        argument_spec=dict(
            ansible_connection=dict(type='str'),
            ansible_host=dict(type='str'),
            ansible_port=dict(type='int'),
            ansible_user=dict(type='str'),
            executor_work_root=dict(type='path'),
            inventory_hostname=dict(type='str'),
            mirror_workspace_quiet=dict(type='bool'),
            zuul_projects=dict(type='dict'),
            zuul_resources=dict(type='dict'),
            zuul_workspace_root=dict(type='path'),
        )
    )

    output = {}
    if for_each_project(sync_one_project, module.params, output):
        module.exit_json(changed=True, output=output)
    else:
        module.fail_json("Failure synchronizing repos", output=output)


if __name__ == '__main__':
    ansible_main()
