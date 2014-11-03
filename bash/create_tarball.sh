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
svn info $ROOTCOREBIN/../SusyNtuple $ROOTCOREBIN/../SusyCommon $ROOTCOREBIN/../MultiLep $ROOTCOREBIN/../SUSYTools > tarBallTags

# We don't need to actually submit a job, but still need to provide some dummy arguments to prun
prun --exec "echo" --tmpDir=$tmpDir --outTarBall=$tarFile --useRootCore --noSubmit --outDS=user.$nickname.DummyDoesNothing

