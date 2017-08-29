#!/bin/bash

nickname=$USER
tmpDir=/tmp/$USER
mkdir -p $tmpDir

tarFile=area.tgz

if [ -e $tarFile ]; then
    echo "Removing old tar file"
    rm $tarFile
fi

# Create a snapshot list of the SVN tags used to make this tarball, useful for when you forget
#${ROOTCOREBIN}/../SusyNtuple/susyntuple/print_area_tag_snapshot.py > tarBallTags

# We don't need to actually submit a job, but still need to provide some dummy arguments to prun
#prun --exec "echo" --tmpDir=$tmpDir --outTarBall=$tarFile --useRootCore --noSubmit --outDS=user.$nickname.DummyDoesNothing
prun --exec "echo" --tmpDir=$tmpDir --outTarBall=$tarFile --useAthenaPackages --cmtConfig=${CMTCONFIG} --noSubmit --outDS=user.$nickname.DummyDoesNothing

