Generate a Zuul manifest file for log uploading

This generates a manifest file in preparation for uploading along
with logs.  The Zuul web interface can fetch this file in order to
display logs from a build.


**Role Variables**

.. zuul:rolevar:: generate_zuul_manifest_root
   :default: {{ zuul.executor.log_root }}

   The root directory to index.

.. zuul:rolevar:: generate_zuul_manifest_filename
   :default: zuul-manifest.json

   The name of the manifest file.

.. zuul:rolevar:: generate_zuul_manifest_output
   :default: {{ zuul.executor.log_root }}/{{ generate_zuul_manifest_filename }}

   The path to the output manifest file.

.. zuul:rolevar:: generate_zuul_manifest_type
   :default: zuul_manifest

   The artifact type to return to Zuul.

.. zuul:rolevar:: generate_zuul_manifest_index_links
   :default: False

   If True, the Zuul dashboard will link to "index.html" for directory
   entries; if False, it will link to the bare directory.
