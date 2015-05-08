#!/bin/env python

#
# SusyNt grid job submit script
# Run with -h to see the options
# You must set up panda tools before running this script
# 
# Examples
#
#  To process all dgemt:
#  > ./python/submit.py susy -f dgemt.txt
#
#  To process period B of data and assign tag n9999:
#  > ./python/submit.py data -p periodB -t n9999
#


from argparse import ArgumentParser
import glob
import re
import subprocess

# Some grid option defaults
defaultTag='n0146'
defaultNickname='sfarrell'
defaultMet='Default'

def main():

    parser = ArgumentParser(description='SusyCommon grid submission')
    add_arg = parser.add_argument
    add_arg('-f', '--input-files', nargs='*', 
            help='input file with datasets, can specify more than one')
    add_arg('-p', '--pattern', default='.*', help='grep pattern to select datasets')
    add_arg('-t', '--tag', default=defaultTag, help='SusyNt tag to assign')
    add_arg('-v', '--verbose', action='store_true', help='verbose output')
    add_arg('--nickname', default=defaultNickname, help='grid nickname, for naming output DS')
    add_arg('--destSE', default='SLACXRD_SCRATCHDISK', 
            help='replicate output dataset to specified site')
    add_arg('--met', default=defaultMet, help='MET flavor to use', 
            choices=['STVF', 'STVF_JVF', 'Default'])
    add_arg('--doMetFix', action='store_true', help='Turns on MET ele-jet overlap fix')
    add_arg('--contTau', action='store_true', help='Store container taus')
    add_arg('--nLepFilter', default='1', help='Number of preselected light leptons to filter on')
    add_arg('--nLepTauFilter', default='2', help='Number of preselected light+tau to filter on')
    add_arg('--filterTrig', action='store_true', help='Turn on trigger filter')
    add_arg('--sys', action='store_true', help='toggle systematics, default skip')
    add_arg('--nFilesPerJob', default=None, help='prun option')
    add_arg('--nGBPerJob', default='10', help='prun option')
    add_arg('--noSubmit', action='store_true', help='test prun without submitting')
    add_arg('--useShortLivedReplicas', action='store_true', help='prun option')
    add_arg('--cmtConfig', default=None, help='prun option to set cmt config')
    add_arg('--saveTruth', action='store_true', help='Store truth info')
    add_arg('--filterOff', action='store_true', help='Disable event filters (GRL...TileTrip)')
    add_arg('--group-role', action='store_true', help='submit jobs with group produ role')
    add_arg('--do-not-store', action='store_true', help='by default, group ntuples are stored also at SWT2_CPB_PHYS-SUSY')
    args = parser.parse_args()


    # Override standards
    input_files = args.input_files
    pattern = args.pattern

    # Blacklisted sites
    with open('./txt/blacklist.txt') as f:
        blacklist = f.read()
        blacklist = blacklist.replace('\n', '')

    # Print job
    print 'Submitting', args.tag
    print 'input file:', input_files
    print 'pattern:   ', pattern

    # Loop over inputs
    for input_file in input_files:
        with open(input_file) as inputs:
            for line in inputs:
                line = line.strip()
                if line.startswith('#') : continue
                info = line.split()
                if len(info) == 0: continue

                # Match pattern
                if re.search(pattern, line) == None: continue

                inDS = info[0]
                # Get sample name
                sample = re.sub('.merge.*', '', inDS)
                sample = re.sub('mc12_8TeV\.[0-9]*\.', '', sample)
                sample = re.sub('.*phys-susy\.', '', sample)
                sample = re.sub('\.PhysCont.*', '', sample)
                sample = re.sub('physics_', '', sample)

                out_ds_suffix='nt' # otherwise prun will use append a default '_susyNt.root'
                outDS = determine_outdataset_name(input_dataset_name=inDS, nt_tag=args.tag,
                                                  use_group=args.group_role, nickname=args.nickname,
                                                  prun_suffix='_'+out_ds_suffix)

                # Grid command
                gridCommand = './bash/gridScript.sh %IN --metFlav ' + args.met
                gridCommand += ' --nLepFilter ' + args.nLepFilter
                gridCommand += ' --nLepTauFilter ' + args.nLepTauFilter
                gridCommand += ' -s ' + sample
                gridCommand += (' --input '+inDS)
                gridCommand += (' --output '+outDS)
                gridCommand += (' --tag '+args.tag)

                # Container taus - forced on, for now
                #gridCommand += ' --saveContTau' if args.contTau else ' --saveTau'
                gridCommand += ' --saveContTau'

                # Met fix
                if args.doMetFix: gridCommand += ' --doMetFix'

                # Trigger filtering
                if args.filterTrig: gridCommand += ' --filterTrig'

                # Truth leptons
                gridCommand += ' --saveTruth' if args.saveTruth else ''

                # Turn off all filtering
                gridCommand += ' --filterOff' if args.filterOff else ''

                # Systematics
                if args.sys: gridCommand += ' --sys'

                # AF2 sample option
                if re.search('_a[0-9]*_', inDS): gridCommand += ' --af2'

                print '\n' + ('_'*90)
                print 'Input   ', inDS
                print 'Output  ', outDS
                print 'Sample  ', sample
                print 'Command ', gridCommand
                print ''

                # The prun command
                prunCommand = 'prun --exec "' + gridCommand + '" --useRootCore --tmpDir /tmp '
                prunCommand += ' --inDS ' + inDS + ' --outDS ' + outDS
                prunCommand += ' --inTarBall=area.tgz --extFile "*.so,*.root" --match "*root*"'
                prunCommand += ' --safetySize=600'
                prunCommand += ' --outputs "{0}:susyNt.root"'.format(out_ds_suffix)
                prunCommand += ' --destSE=' + (args.destSE if not args.group_role else
                                               ','.join([args.destSE, 'SWT2_CPB_PHYS-SUSY','LRZ-LMU_PHYS-SUSY']))
                prunCommand += ' --rootVer=6.02/05 --cmtConfig=x86_64-slc6-gcc48-opt'
                prunCommand += ' --excludedSite=' + blacklist
                prunCommand += ('' if not args.group_role else ' --official --voms atlas:/atlas/phys-susy/Role=production')

                # You can only have one of the following options
                if(args.nFilesPerJob is not None):
                    prunCommand += ' --nFilesPerJob=' + args.nFilesPerJob
                else:
                    prunCommand += ' --nGBPerJob=' + args.nGBPerJob

                # For testing
                if(args.noSubmit): prunCommand += ' --noSubmit'
                if(args.useShortLivedReplicas):
                    prunCommand += ' --useShortLivedReplicas'
                if(args.cmtConfig is not None):
                    prunCommand += ' --cmtConfig ' + args.cmtConfig

                # Execute prun command
                if args.verbose: print prunCommand
                # subprocess.call(prunCommand, shell=True)

def determine_outdataset_name(input_dataset_name, nt_tag, use_group, nickname, prun_suffix='susyNt.root'):
    prefix = 'group.phys-susy.' if use_group else "user.%s."%nickname
    output_ds_name = prefix + re.sub('/', '', input_dataset_name)+'_'+nt_tag+'/'
    output_ds_name = re.sub('NTUP_SUSY', 'SusyNt', output_ds_name)
    output_ds_name = re.sub('NTUP_COMMON', 'SusyNt', output_ds_name)
    output_ds_name = re.sub('AOD', 'SusyNt', output_ds_name)
    output_ds_name = re.sub('DAOD_SUSY1', 'SusyNt', output_ds_name)
    output_ds_name = re.sub('SKIM',      '', output_ds_name)
    output_ds_name = re.sub('merge\.',   '', output_ds_name)
    if output_ds_name.count('group.phys-susy.')>1: # duplication appearing when processing data with group role
        output_ds_name = output_ds_name.replace('group.phys-susy.', '', 1)
    max_ds_length = 132 # enforced ds name limit
    output_ds_name = re.sub('2LeptonFilter', '2L', output_ds_name)
    output_ds_name = re.sub('UEEE3_CTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('AUET2CTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('AUET3CTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('AUET2BCTEQ6L1_', '', output_ds_name)
    output_ds_name = re.sub('AU2CT10_', '', output_ds_name)
    output_ds_name = re.sub('AUET2B_CTEQ6L1_', '', output_ds_name)
    if len(output_ds_name + prun_suffix + '/') > max_ds_length:
        tags_to_keep = "_.*_%s"%nt_tag  # last resort: drop n-2 tags
        regex = "\.SusyNt\.(?P<other_tags>.*)%s"%tags_to_keep
        match = re.search(regex, output_ds_name)
        if match:
            output_ds_name = output_ds_name.replace(match.group('other_tags'), '')
    output_ds_name = output_ds_name.replace('__', '_').replace('..', '.').replace('_.', '.').replace('._', '.')
    return output_ds_name

if __name__ == '__main__':
    main()
