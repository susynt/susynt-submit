#!/bin/env python

#
# Script to submit the jobs to produce SusyNt ntuples
#
# See help message and README for examples.
#
# 2012-2015
# sfarrell@cern.ch
# davide.gerbaudo@gmail.com


from argparse import ArgumentParser
import glob
import re
import subprocess
import sys

def main():
    parser = ArgumentParser(description='NtMaker grid submission')
    add_arg = parser.add_argument
    add_arg('-f', '--input-files', required=True, nargs='*', help='input file with datasets, can specify more than one')
    add_arg('-n', '--nickname', required=True, help='grid nickname, for naming output DS')
    add_arg('-t', '--tag', required=True, help='SusyNt tag to assign')
    add_arg('-p', '--pattern', default='.*', help='grep pattern to select datasets')
    add_arg('-v', '--verbose', action='store_true', help='verbose output')
    add_arg('--destSE', default='SLACXRD_SCRATCHDISK', help='replicate output dataset to specified site')
    add_arg('--contTau', action='store_true', help='Store container taus')
    add_arg('--nLepFilter', default='1', help='Number of preselected light leptons to filter on')
    add_arg('--trigFilter', action='store_true', help='Turn on trigger filter')
    add_arg('--sys', action='store_true', help='toggle systematics, default skip')
    add_arg('--nFilesPerJob', default='5',help='prun option')
    add_arg('--nGBPerJob', help='prun option')
    add_arg('--noSubmit', action='store_true', help='test prun without submitting')
    add_arg('--useNewCode', action='store_true', help='prun opt')
    add_arg('--allowTaskDuplication', action='store_true', help='prun opt')
    add_arg('--useShortLivedReplicas', action='store_true', help='prun option')
    add_arg('--cmtConfig', default=None, help='prun option to set cmt config')
    add_arg('--saveTruth', action='store_true', help='Store truth info')
    add_arg('--filterOff', action='store_true', help='Disable event filters (GRL...TileTrip)')
    add_arg('--group-role', action='store_true', help='submit jobs with group produ role')
    add_arg('--do-not-store', action='store_true', help='by default, group ntuples are stored also at SWT2_CPB_PHYS-SUSY')
    args = parser.parse_args()

    if args.nFilesPerJob and args.nGBPerJob:
        print "args.nFilesPerJob ",args.nFilesPerJob
        print "args.nGBPerJob: ",args.nGBPerJob
        parser.error("prun does not allow to specify both options '--nFilesPerJob' and '--nGBPerJob' at the same time")
    input_files = args.input_files
    pattern = args.pattern
    blacklist = open('./txt/blacklist.txt').read().strip()

    print "Submitting {}\ninput file: {}\npattern:   {}".format(args.tag, input_files, pattern)
    for input_file in input_files:
        with open(input_file) as lines:
            lines = [l.strip() for l in lines if is_interesting_line(line=l,regexp=pattern)]
            for line in lines:
                inDS = line
                sample = determine_sample_name(inDS)
                out_ds_suffix='nt' # otherwise prun will use append a default '_susyNt.root'
                outDS = determine_outdataset_name(input_dataset_name=inDS, nt_tag=args.tag,
                                                  use_group=args.group_role, nickname=args.nickname,
                                                  prun_suffix='_'+out_ds_suffix)
                is_af2_sample = re.search('_a[0-9]*_', inDS)
                is_mc15b_sample = isMC15b(inDS)
                #is_mc15b_sample = ((re.search('_r7267_', inDS) or re.search('_r7326_', inDS) or re.search('_r7360_', inDS) or re.search('_a810_', inDS)) and re.search('_r6282', inDS))
                is_mc15c_sample = isMC15c(inDS)

                is_mc15c_sample = True
                is_mc15b_sample = False

                mc_type = ""
                if is_mc15c_sample and not is_mc15b_sample :
                    mc_type = "mc15c"
                elif is_mc15b_sample and not is_mc15c_sample :
                    mc_type = "mc15b"
                else :
                    print "ERROR Could not get mc_type, exiting"
                    sys.exit()

                # Grid command
                #gridCommand = './bash/gridScript.sh %IN --metFlav ' + args.met
                gridCommand = './bash/gridScript.sh %IN '
                gridCommand += ' --nLepFilter ' + args.nLepFilter
                gridCommand += (' --input '+inDS)
                gridCommand += (' --output '+outDS)
                gridCommand += (' --tag '+args.tag)
                gridCommand += (' --trigFilter' if args.trigFilter else '')
                gridCommand += (' --saveTruth' if args.saveTruth else '')
                #gridCommand += (' --filterOff' if args.filterOff else '')
                gridCommand += (' --sys' if args.sys else '')
                gridCommand += (' --af2' if is_af2_sample else '')
                gridCommand += (' --mctype '+ mc_type)
                gridCommand += (' --contTau') # if args.contTau else '') # forced on, for now
                #print "WARNING FORCING TO RUN ONLY 10000 EVENTS!"
                #gridCommand += (' -n 10000')


                line_break = ('_'*90)
                print "\n{}\nInput {}\nOutput {}\nSample {}\nCommand {}".format(line_break, inDS, outDS, sample, gridCommand)

                # The prun command
                prunCommand =  ('prun --exec "' + gridCommand + '" --useRootCore --tmpDir /tmp ')
                prunCommand += (' --inDS {} --outDS {}'.format(inDS, outDS))
                prunCommand += (' --inTarBall=area.tgz --extFile "*.so,*.root" --match "*root*"')
                prunCommand += (' --safetySize=600')
                prunCommand += (' --excludedSite={}'.format(blacklist))
                prunCommand += (' --outputs "{0}:susyNt.root"'.format(out_ds_suffix))
                prunCommand += (' --nFilesPerJob={}'.format(args.nFilesPerJob) if args.nFilesPerJob else '5')
                prunCommand += (' --nGBPerJob={}'.format(args.nGBPerJob) if args.nGBPerJob else '')
                prunCommand += (' --noSubmit' if args.noSubmit else '')
                prunCommand += (' --useNewCode' if args.useNewCode else '')
                prunCommand += (' --allowTaskDuplication' if args.allowTaskDuplication else '')
                prunCommand += (' --useShortLivedReplicas' if args.useShortLivedReplicas else '')
                prunCommand += (' --rootVer=6.02/05 --cmtConfig=x86_64-slc6-gcc48-opt')
                prunCommand += (' --cmtConfig={}'.format(args.cmtConfig) if args.cmtConfig else '') # conflict with above? DG 2015-05-08
                prunCommand += ('' if not args.group_role else ' --official --voms atlas:/atlas/phys-susy/Role=production')
                prunCommand += (' --destSE=' + (args.destSE if not args.group_role else
                                                ','.join([args.destSE, 'SWT2_CPB_PHYS-SUSY','LRZ-LMU_PHYS-SUSY'])))
                                                #','.join([args.destSE, 'LRZ-LMU_PHYS-SUSY', 'SLACXRD_LOCALGROUPDISK', 'MWT2_UC_LOCALGROUPDISK'])))

                # Execute prun command
                if args.verbose: print prunCommand
                subprocess.call(prunCommand, shell=True)

def isMC15b(input_dataset_name) :
    is_b = False 
    mc15b_digireco_tags = ['_r7267_', '_r7326_', '_r7360_', '_a810_']
    mc15b_merge_tag = '_r6282'
    for tag in mc15b_digireco_tags :
        if re.search(tag, input_dataset_name) and re.search(mc15b_merge_tag, input_dataset_name) :
            is_b = True
    return is_b

def isMC15c(input_dataset_name) :
    is_c = False
    mc15c_digireco_tags = ['_r7725_', '_r7772_', '_a818_', '_a821_', '_r7773_']
    mc15c_merge_tag = '_r7676'
    for tag in mc15c_digireco_tags :
        if re.search(tag, input_dataset_name) and re.search(mc15c_merge_tag, input_dataset_name) :
            is_c = True
    return is_c
        

def determine_outdataset_name(input_dataset_name, nt_tag, use_group, nickname, prun_suffix='susyNt.root'):
    prefix = 'group.phys-susy.' if use_group else "user.%s."%nickname
    output_ds_name = prefix + re.sub('/', '', input_dataset_name)+'_'+nt_tag+'/'
    output_ds_name = re.sub('NTUP_SUSY', 'SusyNt', output_ds_name)
    output_ds_name = re.sub('NTUP_COMMON', 'SusyNt', output_ds_name)
    for i in range(10) :
        output_ds_name = re.sub('DAOD_SUSY%s'%str(i), 'SusyNt', output_ds_name)
    output_ds_name = re.sub('DAOD_HIGG4D1', 'SusyNt', output_ds_name)
    output_ds_name = re.sub('AOD', 'SusyNt', output_ds_name)
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

def determine_sample_name(input_dataset_name=''):
    """from a long input container name, determine a short sample name

    Originally this sample name was used by SusyNtTools to determine
    on the fly a few running options (based on mc/data, signal/bkg,
    etc.). I don't know whether we still need it since we're now
    storing the full input and output container names, but it's nice
    to have a short human-friendly name.
    """
    sample = re.sub('.merge.*', '', input_dataset_name)
    sample = re.sub('mc12_8TeV\.[0-9]*\.', '', sample)
    sample = re.sub('.*phys-susy\.', '', sample)
    sample = re.sub('\.PhysCont.*', '', sample)
    sample = re.sub('physics_', '', sample)
    return sample

def is_interesting_line(line='', regexp=''):
    "interesting line: non-comment, non-empty, one name, matching selection"
    line = line.strip()
    tokens = line.split()
    return (len(line)>0 and not line.startswith('#') and len(tokens)==1 and re.search(regexp, line))

if __name__ == '__main__':
    main()
