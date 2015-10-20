#!/bin/env python
#
# This script will produce a list containing on each
# line a list of incomplete/failed jobs. The determination
# of whether the job has completed or failed is based on the
# log files output from NtMaker where it is assumed that the
# sign-off text "SusyNtMaker job done" is only output when
# the output ntuple has successfully been made.
#
# In the resubmit script we rename the previously run logs
# by appending a suffix with the time-stamp for the time
# when the resubmitted job was submitted. As a result there
# may be multiple instances of a log file for a single sub-job
# of a given dataset. In this case we grab the log with the
# most recent creation time and make our decision about
# failure or success based on that log.
#
# daniel.joseph.antrim@cern.ch
# October 2015

import sys
import glob
from argparse import ArgumentParser
import os
import datetime

def main() :
    parser = ArgumentParser(description="yep")
    add_arg = parser.add_argument
    add_arg("-i", "--input", default="", help="directory of dataset directories", required=True)
    args = parser.parse_args()
    indir = args.input

    #suff = ""
    #if indir.endswith("/") : suff = indir[:-1]
    #else :
    #    suff = indir
    #outname = "incompleteJobs_%s.txt"%suff
    #file_ = open(outname, "w")

    ntlogmap = getNtMakerLogs(indir) # { dsname : [ntlog1, ntlog2, ...] }
    for ds in ntlogmap.keys() :
        logs = ntlogmap[ds]
        for log in logs :
            job_done = False
            lines = open(log).readlines()
            for line in lines :
                if not line : continue
                if "SusyNtMaker job done" in line : job_done = True
            if not job_done :
                #file_.write("%s\n"%log)
                print "%s"%log
    #print "list of incomplete jobs stored at : %s"%outname
    #file_.close()

def getNtMakerLogs(directory = "") :
    """
    For each dataset retrieve the logs for each of its
    sub-jobs.

    Checks for mulitple instances of a single sub-job
    and gets the one with the most recent creation time.
    """
    if directory == "" :
        print "getNtMakerLogs   input directory is blank."
        sys.exit()
    if directory.endswith("/") : directory = directory[:-1]
    ds = glob.glob(directory + "/user*")

    map = {}
    for d in ds :
        map[d] = []
        if d.endswith("/") : d = d[:-1]
        log_dir = d + "/logs/"
        ntlogs = glob.glob(log_dir + "*.out")
        ntlogs = get_latest_created(ntlogs) # when running the resubmit we append a datetime to the output logs, only get the latest one! (based on file's creation time)
        for ntl in ntlogs :
            map[d].append(ntl)
    return map

def get_latest_created(logs) :
    """
    If a given sub-job has multiple instances of a log file,
    pick the log with the most recent creation time.
    """
    duplicates = {} # { base : [ duplicate suffixes ] }
    bases = []
    out_logs = []
    for l in logs :
        str_ = "mc15_13TeV."
        if "data15_13TeV" in l : str_ = "data15_13TeV."
        base = l[:l.find("logs/")+5]
        nickname = l.replace(base, '')
        nickname = nickname[:nickname.find(str_)]
        base += nickname + str_
        run_numbers = l.replace(base, '').split('.')[:2]
        run_numbers = str(run_numbers[0]) + "." + str(run_numbers[1])
        base += run_numbers
        bases.append(base)
    for b in bases :
        duplicates[b] = []
        for l in logs :
            if b in l : duplicates[b].append(l)

    # now we have the repeated logs for each dataset
    # > grab only the latest log
    for b in duplicates.keys() :
        most_recent = creation_date(duplicates[b][0])
        most_recent_log = duplicates[b][0]
        for i, l in enumerate(duplicates[b]) :
            if creation_date(l) > most_recent : most_recent_log = duplicates[b][i]
        out_logs.append(most_recent_log)
    return out_logs

def creation_date(filename) :
    t = os.path.getctime(filename)
    return datetime.datetime.fromtimestamp(t)

#_______________________________________________
if __name__=="__main__" :
    main()
