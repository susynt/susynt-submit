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
        self.parentDataset = ""
        self.subFileName   = ""
        self.condorARGS = ""
        self.logLog = ""
        self.ntLog = ""
        self.errLog = ""
        self.output = ""
        self.outputRemap = ""

    def getParentDataset(self, log) :
        log = log.split("/")
        parent_ds = str(log[1])
        self.parentDataset = parent_ds

    def getSubFileName(self, log) :
        log = log.split("/")
        file_ = log[-1]
        file_ = file_.replace(".out", ".susyNt.root")
        self.subFileName = file_

    def getCondorARGS(self, log) :
        lines = open(log).readlines()
        found_ntmaker = False
        found_start = False
        found_out = False

        start_dir = ""
        out_dir = ""
        ntmaker_options = ""
        for line in lines :
            if found_ntmaker and found_start and found_out: break
            if not line : continue
            line = line.strip()
            if "NtMaker options" in line :
                found_ntmaker = True
                ntmaker_options = line.replace("NtMaker options : ", "")
            elif "start dir" in line :
                found_start = True
                line = line.split(":")
                start_dir = line[1]
            elif "out dir" in line :
                found_out = True
                line = line.split(":")
                out_dir = line[1]

        self.condorARGS = " %s %s %s "%(start_dir, out_dir, ntmaker_options)

    def getLogs(self, log) :
        suff = datetime.datetime.now().strftime("%I%M%p_%b_%d_%y")
        self.logLog = log.replace('.out', '.%s.log'%suff)
        self.ntLog = log.replace('.out', '.%s.out'%suff)
        self.errLog = log.replace('.out', '.%s.err'%suff)

    def getOutputFile(self, log) :
        output_nt = log.split("/")[-1]
        output_nt = output_nt.replace(".out", ".susyNt.root")
        self.output = output_nt
    def getOutputRemap(self, log) :
        trail = log.split("/")[-1]
        remap = log.replace(trail, '')
        remap = remap.replace('logs/', '')

        self.outputRemap = remap

def main() :
    parser = ArgumentParser(description="Condor Submission of Failed Jobs")
    add_arg = parser.add_argument
    add_arg('-f', '--input', required=True, help='Provide the output from the "get_fails.py" script')
    add_arg('-o', '--output-dir', required=True, help='Provide the output directory where all datasets were stored for "submit_condor.py"')
    args = parser.parse_args()

    output_dir = args.output_dir

    failed_datasets = getFailedDatasets(args.input)
    look_for_condor_template(local, sdsc, uc)
    look_for_condor_executable()

    for ds in failed_datasets :
        cmd = 'ARGS="%s" '%ds.condorARGS

        condor_sub_name = getCondorExecutable(ds)
        cmd += "condor_submit %s "%condor_sub_name
        cmd += ' -append "log = %s" '%ds.logLog
        cmd += ' -append "error = %s" '%ds.errLog
        cmd += ' -append "output = %s" '%ds.ntLog

        line_break = "-"*90
        print line_break
        print "Resubmitting %s : %s"%(ds.parentDataset, ds.output)
        subprocess.call(cmd, shell=True)
        cmd = "rm %s"%condor_sub_name
        subprocess.call(cmd, shell=True)

def getCondorExecutable(ds) :
    template_lines = open("submitFile_TEMPLATE.condor").readlines()
    name = 'submitFile_%s.condor'%ds.output
    outfile = open(name, 'w')
    for line in template_lines :
        if not line : continue
        line = line.strip()
        if 'OUTFILE' in line and 'REMAP' not in line :
            line = 'transfer_output_files = %s'%ds.output
            outfile.write(line + "\n")
        elif 'OUTFILE_REMAP' in line :
            path = str(os.path.abspath(ds.outputRemap))
            if path.endswith("/") : path = path[:-1]
            path += "/%s"%ds.output
            line = 'transfer_output_remaps = "%s = %s"'%(ds.output, path)
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
            print "relative path to file (%s) does not exist!"
            print " > please call this script in the same directory that 'submit_condor.py' was called from."
            sys.exit()
        ds = getDataset(log)
        datasets.append(ds)
    return datasets

def getDataset(log) :
    ds = Dataset(log)
    ds.getParentDataset(log)
    ds.getSubFileName(log)
    ds.getCondorARGS(log)
    ds.getLogs(log)
    ds.getOutputFile(log)
    ds.getOutputRemap(log)
    return ds

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

def look_for_condor_template(site_local_ = False, site_sdsc_ = False, site_uc_ = False) :
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
        file_.write('executable = RunNtMaker_CO.sh\n')
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
    if not os.path.isfile('RunNtMaker_CO.sh') :
        print 'Condor executable "RunNtMaker_CO.sh" not found. One will be made.'
    
        file_ = open('RunNtMaker_CO.sh', 'w')
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
        
        


if __name__=="__main__" :
    main()
