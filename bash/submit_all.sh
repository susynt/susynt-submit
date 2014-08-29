#!/usr/bin/env bash

# Commands to submit all susynt jobs
#
# davide.gerbaudo@gmail.com
# 2014-08-28

readonly NICKNAME="${USER}"

function check_env {
    : ${NTTAG:?"Need to set a valid NTTAG, e.g. n0155"}
}

function submit_data {
    local data_files=""
    data_files+=" txt/data/data12_Egamma.txt"
    data_files+=" txt/data/data12_Muons.txt"
    local log_file="./submission_data.log"
    echo "Starting submission : `date`" 2>&1 | tee --append ${log_file}
    local F=""
    for F in ${data_files}
    do    
        ./python/submit.py data --group-role --filterTrig --contTau --nickname ${NICKNAME} -t ${NTTAG} -f ${F} 2>&1 | tee --append ${log_file}
    done
    echo "Completed submission : `date`" 2>&1 | tee --append ${log_file}
}

function submit_background {
    local bkg_files="$(find txt/background/ -name "*.txt")"
    local log_file="./submission_background.log"
    echo "Starting submission : `date`" 2>&1 | tee --append ${log_file}
    local F=""    
    for F in ${bkg_files}
    do    
        ./python/submit.py mc --group-role --saveTruth --contTau --nickname ${NICKNAME} -t ${NTTAG} -f ${F} 2>&1 | tee --append ${log_file}
    done
    echo "Completed submission : `date`" 2>&1 | tee --append ${log_file}
}

function submit_signal {
    local sig_files="$(find txt/signal/p1512/ -name "*.txt")"
    local log_file="./submission_signal.log"
    echo "Starting submission : `date`" 2>&1 | tee --append ${log_file}
    local F=""
    for F in ${sig_files}
    do    
        ./python/submit.py mc --group-role --saveTruth --contTau --filterOff --nickname ${NICKNAME} -t ${NTTAG} -f ${F} 2>&1 | tee --append ${log_file}
    done
    echo "Completed submission : `date`" 2>&1 | tee --append ${log_file}
}

#---------
# main
#---------
check_env
submit_data
submit_background
submit_signal
