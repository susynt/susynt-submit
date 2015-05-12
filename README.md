susynt-submit
=============

Files and scripts needed to submit a SusyNt ntuple production

Instructions
------------

Pre-requisites:

- a directory `build_area` where you have already built all the necessary packages.
  For this step, see [susynt-write](https://github.com/gerbaudo/susynt-write).
- `localSetupROOT` (with the same version used to compile `build_area`)
- `voms-proxy-init` and `localSetupPandaClient`

Quickstart
----------

```
cd susynt-write/

setupATLAS
localSetupDQ2Client --skipConfirm
voms-proxy-init -voms atlas -valid 144:00
localSetupPandaClient currentJedi --noAthenaCheck
rcSetup
rc compile
cd ..

git clone git@github.com:gerbaudo/susynt-submit --branch xaod
cd susynt-submit
bash/create_tarball.sh
```

At this point you can submit the jobs for the samples you need.
Below are some reference options:

```
./submit.py --filterTrig --contTau --nickname ${USER} -t ${TAG} -f txt/datasets/2015/data_egamma.txt
./submit.py --filterTrig --contTau --nickname ${USER} -t ${TAG} -f txt/datasets/2015/data_muons.txt
./submit.py --saveTruth  --contTau --nickname ${USER} -t ${TAG} -f txt/datasets/2015/mc_p1784.txt
# ./submit.py --saveTruth --filterOff --contTau --nickname ${USER} -t ${TAG} -f txt/signal/<list>.txt
```

Notes:
- always save container taus, `--contTau`
- for data it is useful to only write events that pass our triggers,
  `--filterTrig`; the reduction in simulated samples is probably not worth it
- for simulated samples, save the truth information, `--saveTruth`
- for signal samples, disable the lepton filter, `--filterOff`.
  This is useful when one needs to compute the signal efficiency,
  and the reduction would anyway be small.
- `${USER}` and `${TAG}` have to be specified. `${USER}` must match your grid username.

