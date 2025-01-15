# Copyright (c) 2017 Red Hat
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

import os
import shlex
import subprocess
import traceback


command_map = {
    'uname': 'uname -a',
    'network_interfaces': 'ip address show',
    'network_routing_v4': 'ip route show',
    'network_routing_v6': 'ip -6 route show',
    'network_neighbors': 'ip neighbor show',
    'df_i': 'df -i',
    'df_m': 'df -m',
    'proc_cpuinfo': 'cat /proc/cpuinfo',
}


def run_command(command):
    env = os.environ.copy()
    env['PATH'] = '{path}:/sbin:/usr/sbin'.format(path=env['PATH'])
    return subprocess.check_output(
        shlex.split(command),
        stderr=subprocess.STDOUT,
        env=env)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            ipv4_route_required=dict(required=False, type='bool'),
            ipv6_route_required=dict(required=False, type='bool'),
            image_manifest=dict(required=False, type='str'),
            image_manifest_files=dict(required=False, type='list'),
            traceroute_host=dict(required=False, type='str'),
        )
    )

    ipv4_route_required = module.params['ipv4_route_required']
    ipv6_route_required = module.params['ipv6_route_required']
    image_manifest = module.params['image_manifest']
    traceroute_host = module.params['traceroute_host']
    image_manifest_files = module.params['image_manifest_files']
    if not image_manifest_files and image_manifest:
        image_manifest_files = [image_manifest]
    ret = {'image_manifest_files': [], 'traceroute': None}

    for image_manifest in image_manifest_files:
        if image_manifest and os.path.exists(image_manifest):
            ret['image_manifest_files'].append({
                'filename': image_manifest,
                # Do this in python cause it's easier than in jinja2
                'underline': len(image_manifest) * '-',
                'content': open(image_manifest, 'r').read(),
            })
    if traceroute_host:
        v6_passed = False
        try:
            ret['traceroute_v6'] = run_command(
                'traceroute6 -n {host}'.format(host=traceroute_host))
            v6_passed = True
        except (subprocess.CalledProcessError, OSError) as e:
            ret['traceroute_v6_exception'] = traceback.format_exc()
            ret['traceroute_v6_output'] = e.output
            ret['traceroute_v6_return'] = e.returncode
            pass
        v4_passed = False
        try:
            ret['traceroute_v4'] = run_command(
                'traceroute -n {host}'.format(host=traceroute_host))
            v4_passed = True
        except (subprocess.CalledProcessError, OSError) as e:
            ret['traceroute_v4_exception'] = traceback.format_exc()
            ret['traceroute_v4_output'] = e.output
            ret['traceroute_v4_return'] = e.returncode
            pass
        if v6_passed or v4_passed:
            # By default, only require one IP family to have a working route,
            # either version will suffice
            passed = True
        if ipv6_route_required and not v6_passed:
            # Override the result if IPv6 is explicitly required
            passed = False
        if ipv4_route_required and not v4_passed:
            # Override the result if IPv4 is explicitly required
            passed = False
        if not passed:
            module.fail_json(
                msg="The required v4 or v6 route to {traceroute_host} was not"
                    " found. The build node is assumed to be invalid.".format(
                        traceroute_host=traceroute_host), **ret)

    for key, command in command_map.items():
        try:
            ret[key] = run_command(command)
        except subprocess.CalledProcessError:
            pass

    module.exit_json(changed=False, _zuul_nolog_return=True, **ret)

from ansible.module_utils.basic import *  # noqa
from ansible.module_utils.basic import AnsibleModule

if __name__ == '__main__':
    main()
