#!/bin/env python

########################################################
# This script is for submitting xAOD samples for
# SusyNt production (w/ NtMaker) using the Condor 
# batch system on the UC-LHC distributed computing 
# network.
#
# You need to provide (via the '-f' option) a sample
# list of xAOD (DAOD) containers. This script will
# automatically build up the "FAX-namespaced" sample
# list (i.e. a list of the global-logical filenames or
# the "g-LFNs") and use those as inputs to NtMaker.
#
# Call:
#    python submit_condor.py -h (--help)
# for full usage.
#
# Requirements:
#    - a susynt-write repository checked out
#      (git clone -b master git@github.com:susynt/susynt-write.git)
#    - localSetupFAX
#    - ${ROOTCOREBIN} must be defined
#   It is recommended prior to running this script
#   to start from a fresh terminal, move to the 
#   susynt-write directory and do the following:
#     1. localSetupFAX
#     2. lsetup "rcsetup [options]"
#     3. rc find_packages
#     4. rc compile
#
#   This will ensure that when, in RunNtMaker.sh, 
#   the call to "source RootCoreBin/local_setup.sh"
#   will suceeed in setting up the environment for each
#   submission.
#
#  daniel.joseph.antrim@cern.ch
#  October 2015
######################################################


import subprocess
import sys
import os
import glob
from argparse import ArgumentParser
import re

####
fax_is_checked = False

def main() :

    parser = ArgumentParser(description="NtMaker Condor Submission")
    add_arg = parser.add_argument
    add_arg('-o', '--output-dir', default=".", help='Directory to store the datasets. Will be created where this script is called.')
    add_arg('-f', '--input-files', required=True, nargs='*', help='input directory with dataset .txt files, can specify more than one')
    add_arg('-n', '--nEvents', default="-1", help="Set the number of events to process")
    add_arg('--sys', default=False, action='store_true', help='Set whether to run systematics')
    add_arg('--nickname', required=True, help='grid nickname, for naming output DS')
    add_arg('--saveContTau', action='store_true', help='Set to store container taus')
    add_arg('--nLepFilter', default="1", help="Number of preselected light leptons to filter on (>=)")
    add_arg('-t', '--tag', required=True, help='SusyNt tag to assign')
    add_arg('-p', '--pattern', default='.*', help='grep pattern to select datasets')
    add_arg('--cache-only', action='store_true', help='Only build the cache, will not run NtMaker')
    add_arg('--run-site', default='1', help='Set cluster option [1:brick-only, 2:brick+local, 3:brick+local+SDSC, 4:brick+local+SDSC+UCs] (default: 1)')
    args = parser.parse_args()

    tag         = args.tag
    nickname    = args.nickname
    input_files = args.input_files
    nEvents     = float(args.nEvents)
    pattern     = args.pattern
    cache_only  = args.cache_only
    run_site    = args.run_site
    fail_check  = args.fail_check

    site_option   = "brick-only"
    do_site_local = False
    do_site_SDSC  = False
    do_site_UC    = False
    if run_site == "2" :
        site_option   = "brick+local"
        do_site_local = True
    elif run_site == "3" :
        site_option   = "brick+local+SDSC"
        do_site_local = True 
        do_site_SDSC  = True 
    elif run_site == "4" :
        site_option   = "brick+local+SDSC+UC"
        do_site_local = True  
        do_site_SDSC  = True 
        do_site_UC    = True 

    # check that the condor submission script is in the local directory.
    # if not, make it
    look_for_condor_script(site_local_ = do_site_local, site_sdsc_ = do_site_SDSC, site_uc_ = do_site_UC)
    look_for_condor_executable()

    # begin submission process
    cache_or_submit = "Submitting"
    if cache_only : cache_or_submit = "Caching"
    print "{} {}\ninput file: {}\npattern: {}\nsite option: {}".format(cache_or_submit, tag, input_files, pattern, site_option)
    for input_file in input_files :
        with open(input_file) as lines :
            lines = [l.strip() for l in lines if is_interesting_line(line=l, regexp=pattern)]
            check_if_scoped(lines)
            for line in lines :
                line = line.split(':')[1]
                inDS = line
                outDS = determine_outdataset_name(input_dataset_name=inDS, nt_tag = tag, nickname_ = nickname)
                print "\tSubmitting input dataset  : %s"%inDS
                print "\t           output dataset : %s"%outDS
                output_dir_ = args.output_dir
                if output_dir_.endswith('/') : output_dir_ = output_dir_[:-1]
                out_dir = output_dir_ + "/" + outDS
                cmd = "mkdir -p %s"%(out_dir)
                subprocess.call(cmd, shell=True)
                cmd = "mkdir -p %s/logs/"%(out_dir)
                subprocess.call(cmd, shell=True)

                fax_files = get_FAX_files(inDS)
                for sub_sample in fax_files :
                    print "\t             > sub-sample : %s"%sub_sample
                    sub_name = get_sub_sample_name(sample = sub_sample, nickname_ = nickname)
                    condor_name = ''
                    if outDS.endswith('/') : condor_name = outDS[:-1]
                    else : condor_name = outDS
                    condor_name += "_" + sub_name
                    condor_name += ".condor"
                    input_container = inDS

                    ## provide the arguments to the ARGS method in condor
                    sub_file_template = "submitFile_TEMPLATE.condor"

                    #____________________________________________________________________#
                    # Begin building up the submission script and command for NtMaker.py
                    #____________________________________________________________________#

                    run_cmd = ""
                    # Command to run condor is as follows :
                    #    $ ARGS="<string of arguments passed to arguments field of condor sub. script>" condor_submit <condor sub. script> -append "out = <X>" -append "log = <Y>" -append "error = <Z>"
                    #    where X, Y, Z are the directory locations of the std.out, condor logs, and std.err
                    run_cmd += "ARGS="
                    run_cmd += '"' # wrap ARGS in a string

                    # first argument will be the working directory (RunNtMaker will cd here as a first set)
                    env_ = os.environ.get('ROOTCOREBIN')
                    if env_ is None :
                        print "ROOTCOREBIN is not defined. Please setup RootCore (call RootCoreBin/local_setup.sh) before running submission."
                        sys.exit()
                    env_ = env_.replace("RootCoreBin", "")
                    run_cmd += ' %s '%env_

                    # second argument will be the output directory for the susyNt.root files
                    #   > after setting up FAX and RootCore, RunNtMaker will cd here
                    run_cmd += ' %s '%str(os.path.abspath(out_dir))


                    # now add the arguments that will eventually be passed to NtMaker
                    input_              = "-f %s "%sub_sample
                    n_events_           = ""
                    if nEvents > 0 :
                        n_events_       = "-n %s "%str(int(nEvents))
                    sample_             = "-s %s "%sub_name
                    input_container_    = "--input %s "%input_container
                    output_container_   = "--output %s "%outDS
                    do_sys_             = ""
                    if args.sys :
                        do_sys_         = "--sys "
                    cont_taus_          = ""
                    if args.saveContTau :
                        cont_taus_      = "--saveContTau "
                    lep_filter_         = "--nLepFilter %s "%args.nLepFilter
                    tag_                = "--tag %s "%tag

                    run_cmd += input_
                    run_cmd += n_events_
                    run_cmd += sample_
                    run_cmd += input_container_
                    run_cmd += output_container_
                    run_cmd += do_sys_
                    run_cmd += cont_taus_
                    run_cmd += lep_filter_
                    run_cmd += tag_

                    # end string of ARGS, close the string quotes
                    run_cmd += '"'

                    susynt_filename = sub_name + ".susyNt.root"
                    output_file = ' "%s = %s/%s" '%(susynt_filename, str(os.path.abspath(out_dir)), susynt_filename)
                    sub_file = add_output_files(sub_file_template, susynt_filename, output_file)
                    # now call condor_submit
                    run_cmd += ' condor_submit %s '%sub_file

                    # now add the condor submission script fields for the output, log, and error directories
                    log_    = "%s/logs/%s.log"%(str(os.path.abspath(out_dir)), sub_name)
                    output_ = "%s/logs/%s.out"%(str(os.path.abspath(out_dir)), sub_name)
                    error_  = "%s/logs/%s.err"%(str(os.path.abspath(out_dir)), sub_name)

                    run_cmd += ' -append "log = %s" '%log_
                    run_cmd += ' -append "error = %s" '%error_
                    run_cmd += ' -append "output = %s" '%output_

                    # execute the command
                    subprocess.call(run_cmd, shell=True)
                    # clean up the submission file
                    cmd = "rm %s"%sub_file
                    subprocess.call(cmd, shell=True)

def add_output_files(con_file, root_file, output_path_string) :
    inlines = open(con_file).readlines()
    name = 'submitFile_%s.condor'%root_file
    out_file = open(name, 'w')
    for line in inlines :
        if not line : continue
        line = line.strip()
        if 'OUTFILE' in line and 'REMAP' not in line :
            line = 'transfer_output_files = %s'%root_file
            out_file.write(line + "\n")
        elif 'OUTFILE_REMAP' in line :
            line = 'transfer_output_remaps = %s'%output_path_string
            out_file.write(line + "\n")
        else :
            out_file.write(line + "\n")
    out_file.close()

    return name

    

def determine_outdataset_name(input_dataset_name, nt_tag, nickname_) :
    max_ds_length = 132 # enforced ds name limit

    prefix = "user.%s."%nickname_
    output_ds_name = prefix + re.sub('/', '', input_dataset_name) + '_' + nt_tag + '/'
    for ver in xrange(12) :
        output_ds_name = re.sub('DAOD_SUSY%s'%str(ver), 'SusyNt', output_ds_name)
    output_ds_name = re.sub('AOD', 'SusyNt', output_ds_name)
    output_ds_name = re.sub('merge\.', '', output_ds_name)
    if output_ds_name.count('group.phys-susy.')>1:
        output_ds_name = output_ds_name.replace('group.phys-susy.', '', 1)
    output_ds_name = re.sub('2LeptonFilter', '2L', output_ds_name)
    output_ds_name = re.sub('UEEE3_CTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('AUET2CTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('AUET3CTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('AUET2BCTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('AU2CT10_', '', output_ds_name)
    output_ds_name = re.sub('AUET2B_CTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('AZNLOCTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('CT10_', '', output_ds_name)
    output_ds_name = re.sub('A14NNPDF23LO_', '', output_ds_name)

    if len(output_ds_name + '/') > max_ds_length :
        tags_to_keep = "_.*_%s"%nt_tag # last resort: drop n-2 tags
        regex = "\.SusyNt\.(?P<other_tags>.*)%s"%tags_to_keep
        match = re.search(regex, output_ds_name)
        if match :
            output_ds_name = output_ds_name.replace(match.group('other_tags'), '')
    output_ds_name = output_ds_name.replace('__', '_').replace('..', '.').replace('_.', '.').replace('._', '.')
    return output_ds_name

def get_sub_sample_name(sample='', nickname_='') :
    """
    samples returned by fax-get-gLFNs are of form:

    root://atlfax.slac.stanford.edu:1094//atlas/rucio/mc15_13TeV:DAOD_SUSY2.06530782._000001.pool.root.1

    what we want to store:

    user.<nickname>.06530782._000001.susyNt.root
    or
    group.phys-susy.06530782._000001.susyNt.root (if group role)
    """
    out_name = 'user.%s.'%nickname_
    sample = sample.split(':')
    if 'mc15' in sample[-2] :
        out_name += "mc15_13TeV."
    elif 'data15' in sample[-2] :
        out_name += "data15_13TeV_physics_Main." # this may be changed, need to check how SusyNtMaker gets the sample name
    sample = sample[-1]
    sample = sample.split('.')
    out_name += sample[1]
    out_name += '.'
    out_name += sample[2]

    return out_name

def look_for_condor_script(site_local_ = False, site_sdsc_ = False, site_uc_ = False) :
    '''
    will look for the default condor submission
    script "submitFile_TEMPLATE.condor" in the current
    directory

    if it is not found it will be made
    '''

    if not os.path.isfile('submitFile_TEMPLATE.condor') :
        print 'Condor submission script template "submitFile_TEMPLATE.condor" not found. One will be made.'

        site_local = 'false'
        site_sdsc  = 'false'
        site_uc    = 'false'
        if site_local_ : site_local = 'true'
        if site_sdsc_  : site_sdsc  = 'true'
        if site_uc_    : site_uc    = 'true'

        file_ = open('submitFile_TEMPLATE.condor', 'w')
        file_.write('universe = vanilla\n')
        file_.write('+local=true\n')
        file_.write('+site_local=%s\n'%site_local)
        file_.write('+sdsc=%s\n'%site_sdsc)
        file_.write('+uc=%s\n'%site_uc)
        file_.write('transfer_input_files = area.tgz\n')
        file_.write('executable = RunNtMaker.sh\n')
        file_.write('arguments = $ENV(ARGS)\n')
        file_.write('should_transfer_files = YES\n')
        file_.write('when_to_transfer_output = ON_EXIT\n')
        file_.write('transfer_output_files = OUTFILE\n')
        file_.write('transfer_output_remaps = OUTFILE_REMAP\n')
        file_.write('use_x509userproxy = True\n')
        file_.write('notification = Never\n')
        file_.write('queue\n')
        file_.close()

def look_for_condor_executable() :
    '''
    will look for the default condor executable
    "RunNtMaker.sh" in the directory where this
    script is called

    if it is not found it will be made
    '''
    if not os.path.isfile('RunNtMaker.sh') :
        print 'Condor executable "RunNtMaker.sh" not found. One will be made.'
        file_ = open('RunNtMaker.sh', 'w')
        file_.write('#!/bin/bash\n\n\n')
        file_.write('echo " ------- RunNtMaker ------- "\n')
        file_.write('start_dir=${1}\n')
        file_.write('out_dir=${2}\n')
        file_.write('ntmaker_options=${@:3}\n\n')
        file_.write('echo "  start dir       : ${start_dir}"\n')
        file_.write('echo "  out dir         : ${out_dir}"\n')
        file_.write('echo "  NtMaker options : ${ntmaker_options}"\n')
        file_.write('echo ""\n')
        file_.write('#shift the arguments to prevent the atlas script from blindly taking them\n')
        file_.write('while (( "$#" )); do\n')
        file_.write('   shift\n')
        file_.write('done\n\n')
        file_.write('start_dir1=${PWD}\n')
        file_.write('echo "untarring area.tgz"\n')
        file_.write('tar -xzf area.tgz\n\n')
        file_.write('echo "current directory structure:"\n')
        file_.write('ls -ltrh\n\n')
        file_.write('export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase\n')
        file_.write('source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh\n')
        file_.write('cd susynt-write\n')
        file_.write('lsetup fax\n')
        file_.write('source RootCoreBin/local_setup.sh\n')
        file_.write('cd ${start_dir1}\n\n')
        file_.write('echo "calling NtMaker"\n')
        file_.write('NtMaker ${ntmaker_options}\n\n\n')
        file_.write('echo "final directory structure:"\n')
        file_.write('ls -ltrh\n')
        file_.close()

 
def get_FAX_files(input_dataset) :
    global fax_is_checked
    if not fax_is_checked :
        if os.environ.get('STORAGEPREFIX') == None :
            print "STORAGEPREFIX environment variable is empty."
            print "You must call 'localSetupFAX' before running."
            sys.exit()
        fax_is_checked = True

    out_files = []
    cmd = 'fax-get-gLFNs %s > tmp_glfns.txt'%input_dataset
    subprocess.call(cmd, shell=True)
    files = open("tmp_glfns.txt").readlines()
    for file in files :
        if not file : continue
        file = file.strip()
        out_files.append(file)
    cmd = "rm tmp_glfns.txt"
    subprocess.call(cmd, shell=True)
    return out_files


def check_if_scoped(input_lines) :
    n_warnings = 1
    for line in input_lines :
        if (not len(line.split(':')) > 1) and (n_warnings < 11) :
            print "Providing input dataset without scope prefix. Be sure that your outputs are correct (FAX prefers to have scoped datasets but not absolutely necessary). [warning %d/10]"%n_warnings
            n_warnings+=1

def is_interesting_line(line='', regexp='') :
    "interesting line: non-comment, non-empty, one name, matching selection"
    line = line.strip()
    tokens = line.split()
    return (len(line)>0 and not line.startswith('#') and len(tokens)==1 and re.search(regexp, line))



#__________________________________
if __name__ == "__main__" :
    main()
