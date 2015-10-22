#!/bin/env python

import subprocess
import sys
import os
import glob
from argparse import ArgumentParser
import datetime

local = False
sdsc  = False
uc    = False

class Dataset :
    def __init__(self, log_ = "") :
        self.log = log_
        self.sourceCodeDir = ""
        self.outDir = ""
        self.ntmakerOutLog = ""
        self.condorLog = ""
        self.ntmakerErrLog = ""
        self.ntmakerOptions = ""
        self.outputSusyNtName = ""

def main() :
    parser = ArgumentParser(description="Condor Submission of Failed Jobs")
    add_arg = parser.add_argument
    add_arg('-f', '--input', required=True, help='Provide the output from the "get_fails.py" script')
    add_arg('-o', '--output-dir', required=True, help='Provide the output directory where all datasets were stored for "submit_condor.py"')
    add_arg('--brick', action='store_true', default=False, help='set whether to allow for jobs to run on the brick')
    add_arg('--local', action='store_true', default=False, help='set whether to allow for jobs to run at UCI')
    add_arg('--sdsc',  action='store_true', default=False, help='set whether to allow for jobs to run at SDSC')
    add_arg('--uc',    action='store_true', default=False, help='set whether to allow for jobs to run at other UCs')
    args = parser.parse_args()

    output_dir = args.output_dir
    run_site_brick = args.brick
    run_site_local = args.local
    run_site_sdsc  = args.sdsc
    run_site_uc    = args.uc

    if not run_site_brick and not run_site_local and not run_site_sdsc and not run_site_uc :
        print "No site has been specified! Specify one or any combination."
        print " > '--brick' : set to run on the brick"
        print " > '--local' : set to run at UCI"
        print " > '--sdsc'  : set to run at SDSC"
        print " > '--uc'    : set to run at other UCs"

    print "________________________________"
    print "Running with following sites"
    print "    brick : %s"%run_site_brick
    print "    local : %s"%run_site_local
    print "    sdsc  : %s"%run_site_sdsc
    print "    uc    : %s"%run_site_uc
    print "________________________________"


    failed_datasets = getFailedDatasets(args.input)
    look_for_condor_script(run_site_brick, run_site_local, run_site_sdsc, run_site_uc)
    look_for_condor_executable()
    look_for_tarball()

    for ds in failed_datasets :
        cmd = 'ARGS="%s" '%getCondorARGS(ds)

        condor_sub_name = getCondorExecutable(ds)
        cmd += "condor_submit %s "%condor_sub_name

        time_stamp = datetime.datetime.now().strftime("%I%M%p_%b_%d_%y")
        cmd += ' -append "log = %s" '%(ds.condorLog.replace(".log", ".%s.log"%time_stamp).strip())
        cmd += ' -append "error = %s" '%(ds.ntmakerErrLog.replace(".err", ".%s.err"%time_stamp).strip())
        cmd += ' -append "output = %s" '%(ds.ntmakerOutLog.replace(".out", ".%s.out"%time_stamp).strip())

        line_break = "-"*90
        print line_break
        print "Resubmitting %s : %s"%(ds.log.replace(output_dir+"/", "",1)[:ds.log.find('/logs')], ds.outputSusyNtName)
        subprocess.call(cmd, shell=True)
        cmd = "rm %s"%condor_sub_name
        subprocess.call(cmd, shell=True)

def getCondorExecutable(ds) :
    template_lines = open("submitFile_TEMPLATE.condor").readlines()
    suff = ds.outputSusyNtName.replace(".susyNt.root", "")
    name = 'submitFile_%s.condor'%suff
    outfile = open(name, 'w')
    for line in template_lines :
        if not line : continue
        line = line.strip()
        if 'OUTFILE' in line and 'REMAP' not in line :
            line = 'transfer_output_files = %s'%ds.outputSusyNtName
            outfile.write(line + "\n")
        elif 'OUTFILE_REMAP' in line :
            path = str(os.path.abspath(ds.outDir))
            if path.endswith("/") : path = path[:-1]
            path += "/%s"%ds.outputSusyNtName
            line = 'transfer_output_remaps = "%s = %s"'%(ds.outputSusyNtName, path)
            outfile.write(line + "\n")
        else :
            outfile.write(line + "\n")
    outfile.close()
    return name


def getFailedDatasets(filelist) :
    datasets = []
    logs = []
    lines = open(filelist).readlines()
    for line in lines :
        if not line : continue
        if line.startswith("#") : continue
        line = line.strip()
        logs.append(line)
    for log in logs :
        if not os.path.isfile(log) :
            print "relative path to file (%s) does not exist!"%log
            print " > please call this script in the same directory that 'submit_condor.py' was called from."
            sys.exit()
        ds = getDataset(log)
        datasets.append(ds)
    return datasets

def getDataset(log) :
    ds = Dataset(log)
    lines = open(log).readlines()
    ds.sourceCodeDir = getSourceCodeDir(lines)
    ds.outDir = getOutputDirectory(lines)
    ds.ntmakerOutLog = getNtMakerOutLogName(lines)
    ds.condorLog = getCondorLogName(lines)
    ds.ntmakerErrLog = getNtMakerErrLogName(lines)
    ds.ntmakerOptions = getNtMakerOptions(lines)
    ds.outputSusyNtName = getOutputNtName(lines)
    #print "source code dir     : %s"%ds.sourceCodeDir
    #print "out dir             : %s"%ds.outDir
    #print " ntmaker out log    : %s"%ds.ntmakerOutLog
    #print "condor log          : %s"%ds.condorLog
    #print "ntmaker err log     : %s"%ds.ntmakerErrLog
    #print "ntmaker options     : %s"%ds.ntmakerOptions
    #print "output susy nt name : %s"%ds.outputSusyNtName
    #sys.exit()
    return ds

def getCondorARGS(dataset) :
    args=""
    args+=' %s '%dataset.sourceCodeDir
    args+=' %s '%dataset.outDir
    args+=' %s '%dataset.ntmakerOutLog
    args+=' %s '%dataset.condorLog
    args+=' %s '%dataset.ntmakerErrLog
    args+=' %s '%dataset.ntmakerOptions
    return args

def getSourceCodeDir(log_lines) :
    source_ = ""
    for line in log_lines :
        if not line : continue
        line = line.strip()
        if "source code dir" in line :
            line = line.split(":")
            source_ = line[1].strip()
            break
    return source_

def getOutputDirectory(log_lines) :
    outdir_ = ""
    for line in log_lines :
        if not line : continue
        line = line.strip()
        if "out dir" in line :
            line = line.split(":")
            outdir_ = line[1].strip()
            break
    return outdir_

def getNtMakerOutLogName(log_lines) :
    name_ = ""
    for line in log_lines :
        if not line : continue
        line = line.strip()
        if "NtMaker output log" in line :
            line = line.split(":")
            name_ = line[1].strip()
            break
    return name_

def getCondorLogName(log_lines) :
    name_ = ""
    for line in log_lines :
        if not line : continue
        line = line.strip()
        if "condor log dir" in line :
            line = line.split(":")
            name_ = line[1].strip()
            break
    return name_

def getNtMakerErrLogName(log_lines) :
    name_ = ""
    for line in log_lines :
        if not line : continue
        if "NtMaker error log" in line :
            line = line.split(":")
            name_ = line[1].strip()
            break
    return name_

def getNtMakerOptions(log_lines) :
    options_ = ""
    for line in log_lines :
        if not line : continue
        if "NtMaker options" in line :
            line = line.replace("NtMaker options", "")
            line = line.replace(":", "", 1)
            options_ = line.strip()
            break
    return options_

def getOutputNtName(log_lines) :
    name_ = ""
    for line in log_lines :
        if not line : continue
        if "NtMaker options" in line :
            line = line.split()
            for iopt, ival in enumerate(line) :
                if ival == "-s" :
                    name_ = line[iopt + 1].strip() + ".susyNt.root"
            break
    return name_

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
            #continue
        elif 'OUTFILE_REMAP' in line :
            line = 'transfer_output_remaps = %s'%output_path_string
            out_file.write(line + "\n")
            #continue
        else :
            out_file.write(line + "\n")
    out_file.close()

    return name

def look_for_condor_script(site_brick_ = False, site_local_ = False, site_sdsc_ = False, site_uc_ = False) :
    '''
    will look for the default condor submission
    script "submitFile_TEMPLATE.condor" in the current
    directory

    if it is not found it will be made
    '''

   # if not os.path.isfile('submitFile_TEMPLATE.condor') :
   # print 'Condor submission script template "submitFile_TEMPLATE.condor" not found. One will be made.'
    print 'Making Condor submission script template "submitFile_TEMPLATE.condor".'

    site_brick = 'false'
    site_local = 'false'
    site_sdsc  = 'false'
    site_uc    = 'false'
    if site_brick_ : site_brick = 'true'
    if site_local_ : site_local = 'true'
    if site_sdsc_  : site_sdsc  = 'true'
    if site_uc_    : site_uc    = 'true'

    file_ = open('submitFile_TEMPLATE.condor', 'w')
    file_.write('universe = vanilla\n')
    file_.write('+local=%s\n'%site_brick)
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
    print 'Making condor executable "RunNtMaker.sh"'
    file_ = open('RunNtMaker.sh', 'w')
    file_.write('#!/bin/bash\n\n\n')
    file_.write('echo " ------- RunNtMaker ------- "\n')
    file_.write('start_dir=${1}\n')
    file_.write('out_dir=${2}\n')
    file_.write('out_log_dir=${3}\n')
    file_.write('log_log_dir=${4}\n')
    file_.write('err_log_dir=${5}\n')
    file_.write('ntmaker_options=${@:6}\n\n')
    file_.write('echo "  source code dir    : ${start_dir}"\n')
    file_.write('echo "  out dir            : ${out_dir}"\n')
    file_.write('echo "  NtMaker output log : ${out_log_dir}"\n')
    file_.write('echo "  condor log dir     : ${log_log_dir}"\n')
    file_.write('echo "  NtMaker error log  : ${err_log_dir}"\n')
    file_.write('echo "  NtMaker options    : ${ntmaker_options}"\n')
    file_.write('echo ""\n')
    file_.write('#shift the arguments to prevent the atlas script from blindly taking them\n')
    file_.write('while (( "$#" )); do\n')
    file_.write('   shift\n')
    file_.write('done\n\n')
    file_.write('work_dir=${PWD}\n')
    file_.write('echo "untarring area.tgz"\n')
    file_.write('tar -xzf area.tgz\n\n')
    file_.write('echo "done untarring"\n')
    file_.write('echo "current directory structure:"\n')
    file_.write('ls -ltrh\n\n')
    file_.write('export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase\n')
    file_.write('source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh\n')
    file_.write('cd susynt-write\n')
    file_.write('lsetup fax\n')
    file_.write('source RootCoreBin/local_setup.sh\n')
    file_.write('cd ${work_dir}\n\n')
    file_.write('echo "calling NtMaker"\n')
    file_.write('NtMaker ${ntmaker_options}\n\n\n')
    file_.write('echo "final directory structure:"\n')
    file_.write('ls -ltrh\n')
    file_.close()

def look_for_tarball() :
    if not os.path.isfile("area.tgz") :
        print "ERROR    expected tarball ('area.tgz') of susynt-write/ directory is not found!"
        sys.exit()


if __name__=="__main__" :
    main()
