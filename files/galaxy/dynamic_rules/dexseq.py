from galaxy.jobs import JobDestination
import os

def dexseq_memory_mapper( job, tool ):
    # Assign admin users' jobs to special admin_project.
    # Allocate extra time
    inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
    inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
    gtf_file = inp_data[ "gtf" ].file_name
    vmem = 5200
    cores = 6
    params = {}
    gtf_file_size = os.path.getsize(gtf_file) / (1024*1024.0)
    if gtf_file_size > 150:
        vmem = 30000
        cores = 6

    # TODO(hxr): fix?
    # params["nativeSpecification"] = """
         # -q galaxy1.q,all.q -l galaxy1_slots=1 -l h_vmem=%sM -pe "pe*" %s  -v
         # _JAVA_OPTIONS -v TEMP -v TMPDIR -v PATH -v PYTHONPATH -v
         # LD_LIBRARY_PATH -v XAPPLRESDIR -v GDFONTPATH -v GNUPLOT_DEFAULT_GDFONT
         # -v MPLCONFIGDIR -soft -l galaxy1_dedicated=1
        # """ % (vmem, cores)
    params['request_memory'] = vmem / 1024
    params['request_cpus'] = cores
    params['priority'] = 128
    env = {
        '_JAVA_OPTIONS': "-Xmx4G -Xms1G",
    }

    return JobDestination(id="dexseq_dynamic_memory_mapping", runner="condor", params=params, env=env)
    # return JobDestination(id="dexseq_dynamic_memory_mapping", runner="drmaa", params=params)
