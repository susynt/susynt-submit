#!/bin/env python

# util functions for logging and monitoring the susynt production
#
# davide.gerbaudo@gmail.com
# 2014-08

import os
import re
import sys

def monitoring_link_from_logfile(logfilename):
    "given a submission logfile, provide the bigpanda monitoring link"
    regexp = re.compile('succeeded. new jediTaskID=(?P<taskid>\d+)')
    taskids = []
    for l in open(logfilename).readlines():
        match = regexp.search(l)
        if match:
            taskids.append(int(match.group('taskid')))
    taskids.sort()
    url = ('http://bigpanda.cern.ch'
           '/prodsys/prodtask/task_table/#/?'
           'time_period=all'
           '&task_type=analysis'
           '&username={0[user]}'
           '&task_id_lt={0[first_task]}'
           '&task_id_gt={0[last_task]}').format({'user':'Daniel%20Antrim',
                                                  'first_task' : taskids[0],
                                                  'last_task' : taskids[-1]})
    return url

# todo : use google url shortener
# todo : parse and look for failures

if __name__=='__main__':
    print monitoring_link_from_logfile(sys.argv[1])
