#!/bin/bash


echo " ------- RunNtMaker ------- "
start_dir=${1}
out_dir=${2}
ntmaker_options=${@:3}

echo "  start dir       : ${start_dir}"
echo "  out dir         : ${out_dir}"
echo "  NtMaker options : ${ntmaker_options}"
echo ""

#shift the arguments to prevent the atlas script from blindly taking them
while (( "$#" )); do
    shift
done

echo "RunNtMaker    Moving to starting directory : ${start_dir}"
cd ${start_dir}

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh

localSetupFAX
source RootCoreBin/local_setup.sh
#lsetup "rcsetup Base,2.3.28"
#rc find_packages
#rc compile
#source rcSetup.sh

echo "RunNtMaker    Moving to output directory : ${out_dir}"
cd ${out_dir}

NtMaker ${ntmaker_options}
#NtMaker -f ${input} -s ${sample} --input ${input_container} --output ${output_container} #-n 50
