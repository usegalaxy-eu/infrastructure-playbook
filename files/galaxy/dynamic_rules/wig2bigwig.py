from galaxy.jobs import JobDestination
import os

def wig_to_bigwig( job, tool ):
    # wig_to_bigwig needs a lot of memory if the input file is big
    inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
    inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
    wig_file = inp_data[ "input1" ].file_name
    wig_file_size = os.path.getsize(wig_file) / (1024*1024.0)

    # according to http://genome.ucsc.edu/goldenpath/help/bigWig.html
    # wig2bigwig uses a lot of memory; somewhere on the order of 1.5 times more memory than the uncompressed wiggle input file
    required_memory = min(max(wig_file_size * 3.0, 16 * 1024), 250*1024) # our biggest memory node has 256GB memory
    params = {}
    # params["nativeSpecification"] = """ -q galaxy1.q,all.q -p -128 -l galaxy1_slots=1 -l h_vmem=%sM -v _JAVA_OPTIONS -v TEMP -v TMPDIR -v PATH -v PYTHONPATH -v LD_LIBRARY_PATH -v XAPPLRESDIR -v GDFONTPATH -v GNUPLOT_DEFAULT_GDFONT -v MPLCONFIGDIR -soft -l galaxy1_dedicated=1 """ % (required_memory)
    params['request_memory'] = required_memory / 1024

    return JobDestination(id="wig_to_bigwig_job_destination", runner="condor", params=params)
