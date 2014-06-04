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
cd build_area
source RootCore/scripts/setup.sh
cd -
git clone git@github.com:gerbaudo/susynt-submit
cd susynt-submit
localSetupPandaClient
./bash/create_tarball.sh
```

At this point you can submit the jobs for the samples you need.
Below are some reference options:

```
./submit.py data --filterTrig --contTau --nickname ${USER} -t ${TAG} -f txt/data/<list>.txt
./submit.py mc   --saveTruth --contTau  --nickname ${USER} -t ${TAG} -f txt/background/<list>.txt
./submit.py mc   --saveTruth --filterOff --contTau --nickname ${USER} -t ${TAG} -f txt/signal/<list>.txt
```

Notes:
- always save container taus, `--contTau`
- for data it is useful to only write events that pass our triggers,
  `--filterTrig`; the reduction in simulated samples is probably not worth it
- for simulated samples, save the truth information, `--saveTruth`
- for signal samples, disable the lepton filter, `--filterOff`.
  This is useful when one needs to compute the signal efficiency,
  and the reduction would anyway be small.

