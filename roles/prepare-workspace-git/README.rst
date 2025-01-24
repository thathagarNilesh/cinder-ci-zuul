Mirror the local git repos to remote nodes

This role uses git operations (unlike :zuul:role:`prepare-workspace`
which uses rsync) to mirror the locally prepared git repos to the remote
nodes while taking advantage of cached repos on the node if they exist.
This role works generically regardless of the existence of a cached
repo on the node.

The cached repos need to be placed using the canonical name under the
`cached_repos_root` directory.

**Role Variables**

.. zuul:rolevar:: cached_repos_root
   :default: /opt/git

   The root of the cached repos.

.. zuul:rolevar:: prepare_workspace_sync_required_projects_only
   :type: bool
   :default: False

   A flag which if set to true, filters the to be synchronized project
   list to only use projects which are required by the job.

.. zuul:rolevar:: mirror_workspace_quiet

   This value is ignored; it should be removed from job configuration.

.. zuul:rolevar:: zuul_workspace_root
   :default: "{{ ansible_user_dir }}"

   The root of the workspace in which the repos are mirrored.
