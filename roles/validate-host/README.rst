Log information about the build node

**Role Variables**

.. zuul:rolevar:: zuul_site_ipv4_route_required
   :default: false

   If true, fail when no IPv4 route to ``zuul_site_traceroute_host`` is
   available. When false (default) a missing IPv4 route is acceptable
   so long as there is still a viable IPv6 route.

.. zuul:rolevar:: zuul_site_ipv6_route_required
   :default: false

   If true, fail when no IPv6 route to ``zuul_site_traceroute_host`` is
   available. When false (default) a missing IPv6 route is acceptable
   so long as there is still a viable IPv4 route.

.. zuul:rolevar:: zuul_site_traceroute_host

   If defined, a host to run a traceroute against to verify build node
   network connectivity.

.. zuul:rolevar:: zuul_site_image_manifest_files
   :default: ['/etc/dib-builddate.txt', '/etc/image-hostname.txt']

   A list of files to read from the filesystem of the build node and
   whose contents will be logged. The default files are files written
   to nodes by diskimage-builder.
