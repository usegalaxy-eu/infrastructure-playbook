from galaxy.jobs import JobDestination
import os


def blast_destinations( job, tool ):
    # Allocate extra time
    inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
    inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
    query_file = inp_data[ "query" ].file_name
    vmem = 2000
    cores = 6

    inp_params = dict( [ ( param.name, param.value ) for param in job.parameters ] )

    blast_type = inp_params.get( "blast_type", 'None' )
    if str(blast_type) == '"dc-megablast"':
        # vmem per core and in MB
        vmem = 6000
        cores = 5

    sizeBinMap = {}
    binPriorityMap = {}
    params = {}
    query_file_size = os.path.getsize(query_file) / (1024*1024.0)

    params["nativeSpecification"] = """-l galaxy1_slots=1 -l h_vmem=%sM -pe "pe*" %s  -v _JAVA_OPTIONS -v TEMP -v TMPDIR -v PATH -v PYTHONPATH -v LD_LIBRARY_PATH -v XAPPLRESDIR -v GDFONTPATH -v GNUPLOT_DEFAULT_GDFONT -v MPLCONFIGDIR -soft -l galaxy1_dedicated=1  """ % (vmem, cores)

    if query_file_size < 5:
        params["nativeSpecification"] += " -p -129 "
    else:
        params["nativeSpecification"] += " -hard -l hblast=1 "
        for c, i in enumerate( range(5, 1000, (1000-5)/100) ):
            sizeBinMap[i] = c


        for c, i in enumerate( range(130, 512, (512-130)/100) ):
            binPriorityMap[c] = i

        query_bin = 1
        for bound in sorted(sizeBinMap):
            if query_file_size > bound:
                query_bin = sizeBinMap[bound]
        params["nativeSpecification"] += " -p -%s" % binPriorityMap[query_bin]

    params['request_memory'] = vmem / 1024
    params['request_cpus'] = cores
    params['priority'] = 128

    # return JobDestination(id="blast_dynamic_job_destination", runner="drmaa", params=params)
    return JobDestination(id="blast_dynamic_job_destination", runner="condor", params=params)
