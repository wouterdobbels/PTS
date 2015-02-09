#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package do.eagle_synchronize Synchronize EAGLE results between remote hosts
#
# This script copies the EAGLE SKIRT results generated on remote hosts (currently only the Cosma cluster in Durham)
# to a central place (currently Peter's Mac at work). Only results for jobs with run-status "completed" are copied.
# The script uses rsync to avoid copying data that is already up to date at the destination.
#

# -----------------------------------------------------------------

import os.path
import subprocess
import eagle.config as config
from eagle.database import Database
from eagle.skirtrun import SkirtRun

# -----------------------------------------------------------------

cosma_prefix = "pcamps@cosma-a.cosma.dur.ac.uk:"

# -----------------------------------------------------------------

# copy the cosma database to obiwan so we have a backup and we can open it locally
print "--> Copying database from cosma to obiwan backup area..."
cosma_database_path = os.path.join(config.cosma["database_path"], "SKIRT-runs.db")
backup_database_path = os.path.join(config.backup_path, "cosma_SKIRT-runs_backup_"+config.timestamp()+".db")
subprocess.call(("rsync", "-htz", cosma_prefix+cosma_database_path, backup_database_path))

# extract records for all completed SKIRT-runs from the local copy of the cosma database
db = Database(backup_database_path)
records = db.select("runstatus = 'completed'")
db.close()
print "--> Cosma has {} completed SKIRT-runs".format(len(records))

# synchronize the results from each completed run
db = Database()
for record in records:
    runid = record['runid']
    print "--> Synchronizing results for run-id {}...".format(runid)

    # get the local and remote paths (creating the local directories if needed)
    skirtrun = SkirtRun(runid, create=True)
    local_runpath = skirtrun.runpath()
    local_inpath = skirtrun.inpath()
    local_outpath = skirtrun.outpath()
    local_vispath = skirtrun.vispath()
    remote_runpath = local_runpath.replace(config.results_path, config.cosma["results_path"])
    remote_inpath = local_inpath.replace(config.results_path, config.cosma["results_path"])
    remote_outpath = local_outpath.replace(config.results_path, config.cosma["results_path"])
    remote_vispath = local_vispath.replace(config.results_path, config.cosma["results_path"])

    # synchronize the files in each directory
    #  - skip subdirectories and symbolic links
    #  - for the vis directory, do not overwrite newer local versions
    subprocess.call(("rsync", "-htvz", cosma_prefix+remote_runpath+"/*", local_runpath+"/"))
    subprocess.call(("rsync", "-htvz", cosma_prefix+remote_inpath+"/*", local_inpath+"/"))
    subprocess.call(("rsync", "-htvz", cosma_prefix+remote_outpath+"/*", local_outpath+"/"))
    subprocess.call(("rsync", "-htvz", "--update", cosma_prefix+remote_vispath+"/*", local_vispath+"/"))

    # update the record in the local database if needed
    if db.updaterow(runid, record): db.commit()

db.close()

print "--> Done synchronizing {} completed SKIRT-runs".format(len(records))

# -----------------------------------------------------------------
