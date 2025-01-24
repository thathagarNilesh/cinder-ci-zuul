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

import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor


def run(cmd, shell=False, cwd=None, check=True, env=None):
    if not shell:
        cmd = shlex.split(cmd)
    return subprocess.run(cmd, shell=shell, cwd=cwd, env=env,
                          stderr=subprocess.STDOUT,
                          stdout=subprocess.PIPE,
                          check=check)


def for_each_project(func, args, output):
    # Run a function for each zuul project in a threadpool executor.
    # An output dictionary specific to that project is passed to the
    # function.
    success = True
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for project in args['zuul_projects'].values():
            project_out = {}
            output[project['canonical_name']] = project_out
            f = executor.submit(
                func, args, project, project_out)
            futures.append((project_out, f))
        for (project_out, f) in futures:
            try:
                f.result()
            except Exception as e:
                msg = str(e)
                if hasattr(e, 'output'):
                    msg = '%s : %s' % (str(e), e.output)
                else:
                    msg = str(e)
                project_out['error'] = msg
                success = False
    return success
