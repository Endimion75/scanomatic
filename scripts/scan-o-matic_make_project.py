#!/usr/bin/env python
"""Module runs subprocess that makes projects."""
__author__ = "Martin Zackrisson"
__copyright__ = "Swedish copyright laws apply"
__credits__ = ["Martin Zackrisson"]
__license__ = "GPL v3.0"
__version__ = "0.9991"
__maintainer__ = "Martin Zackrisson"
__email__ = "martin.zackrisson@gu.se"
__status__ = "Development"

#
# DEPENDENCIES
#

import sys
import os
import threading
import time
import re
import shutil
from argparse import ArgumentParser
from ConfigParser import ConfigParser
"""
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
    level=logging.INFO)
"""
#
# INTERNAL-DEPENDENCIES
#

import src.subprocs.communicator as communicator
import src.resource_project_log as resource_project_log
import src.resource_path as resource_path
import src.resource_first_pass_analysis as resource_first_pass_analysis
import src.resource_logger as logging

#
# CONSTANTS
#

#
# CLASS
#


class Make_Project(object):

    CONFIG_OTHER = "Run Info"
    CONFIG_META = "Meta Data"

    def __init__(self, inputFile, comm_id):

        self._time_init = time.time()
        self._running = None
        self._paused = False

        self._paths = resource_path.Paths()

        self._stdin = self._paths.log_rebuild_in.format(comm_id)
        self._stdout = self._paths.log_rebuild_out.format(comm_id)
        self._stderr = self._paths.log_rebuild_err.format(comm_id)

        logging.setLoggingTarget(self._stderr)
        self._logger = logging.getLogger('Scan-o-Matic Make Project')
        self._set_from_file(inputFile)

        self._comm = communicator.Communicator(
            self,  self._stdin, self._stdout, None)

        self._comm_thread = threading.Thread(target=self._comm.run)

    def _set_from_file(self, fpath):

        config = ConfigParser()
        config.readfp(open(fpath))

        #Gathering the metadata
        self._meta_data = eval(config.get(self.CONFIG_META, 'meta-data'))
        try:
            self._startTime = float(self._meta_data['Start Time'])
        except:
            self._startTime = 0
        try:
            self._interval = float(self._meta_data['Interval'])
        except:
            self._interval = 20.0

        #Gathering the run info
        tmpOther = config.items(self.CONFIG_OTHER)
        self._model = {k: v for k, v in tmpOther}
        for k in ('image-list', 'run-error', 'use-local-fixture',
                  'run-complete'):

            self._model[k] = eval(self._model[k])

        self._images_total = len(self._model['image-list'])

    def _init_output_file(self):

        #Outdata path
        p = os.path.join(self._model['output-directory'],
                         self._model['output-file'])

        md = resource_project_log.get_meta_data_dict(
            **self._meta_data)
        #Make header row for file:
        if resource_project_log.write_log_file(p, meta_data=md) is False:

            self._running = False

            self._logger.error("Could not write {0} to {1}".format(md, p))

        self._output_path = p

    def _init_fixture(self):

        local_fixture_path = None

        #Variable preparation (rfpa = resource_first_pass_analysis)
        self._logger.debug(
            ('Local {0}, LocalName {1} ' +
             'ModelName {2} Gobal Path {3}').format(
                 self._model['use-local-fixture'],
                 self._paths.experiment_local_fixturename,
                 self._meta_data['Fixture'],
                 self._paths.fixtures))

        if self._model['use-local-fixture']:
            rfpa_fixture = self._paths.experiment_local_fixturename
            rfpa_f_dir = self._model['output-directory']
        else:
            rfpa_fixture = self._meta_data['Fixture']
            rfpa_f_dir = self._paths.fixtures
            local_fixture_path = os.path.join(
                self._model['output-directory'],
                self._paths.experiment_local_fixturename)

            #Take backup of previous local fixture config if exists
            if (local_fixture_path is not None and
                    os.path.isfile(local_fixture_path)):

                shutil.copyfile(
                    local_fixture_path,
                    local_fixture_path + ".old")

            #Copy global fixutre config into directory
            shutil.copyfile(
                self._paths.get_fixture_path(
                    self._meta_data['Fixture'],
                    own_path=self._paths.experiment_local_fixturename),
                local_fixture_path)

        self._fixture_name = rfpa_fixture
        self._fixture_dir = rfpa_f_dir

    def _analyse_image(self, im_path):

        try:
            im_acq_time = float(re.findall(r'([0-9.]*)\.tiff$', im_path)[-1])
            if self._image_i == 0:
                im_acq_time = 0.0
        except:
            im_acq_time = self._image_i * self._interval

        self._logger.info("Processing '{0}' as time {1}".format(
            im_path, im_acq_time))

        #Analyse image
        im_data = resource_first_pass_analysis.analyse(
            im_path,
            im_acq_time=im_acq_time,
            fixture_name=self._fixture_name,
            fixture_directory=self._fixture_dir,
            experiment_directory=None)

        if im_data['grayscale_indices'] is None:

            self._logger.error("Could not find target values for Grayscale")

        elif im_data['grayscale_values'] is None:
            self._logger.error("Could not analyse grayscale on '{0}'".format(
                im_path))
        else:

            #Get proper dict for writing to file
            im_dict = resource_project_log.get_image_dict(
                im_path,
                im_data['Time'],
                im_data['mark_X'],
                im_data['mark_Y'],
                im_data['grayscale_indices'],
                im_data['grayscale_values'],
                im_data['scale'],
                img_dict=im_data,
                image_shape=im_data['im_shape'])

            #Write results
            if resource_project_log.append_image_dicts(
                    self._output_path, images=[im_dict]) is False:

                self._logger.error(
                    "Could not write data for {0} to {1}".format(
                        self._output_path, im_dict))

    def run(self):

        self._time_run_start = time.time()
        self._running = True
        self._image_i = 0

        #WRITE METADATA HEADER
        self._init_output_file()

        #Communicator starts now, since now it is safe
        self._comm_thread.start()

        #SET UP FIXTURE
        self._init_fixture()

        self._logger.debug("Ready to go through {0} images {1}".format(
            self._images_total, self._running))

        #DO THE IMAGES
        while self._running and self._image_i < self._images_total:

            #DO THE FIRST PASS
            self._analyse_image(self._model['image-list'][self._image_i])
            self._logger.info("Done processing {0} of {1}".format(
                self._image_i + 1, self._images_total))

            self._image_i += 1

            while self._paused and self._running:

                time.sleep(0.42)

        self._logger.info("Shutting down")

        #Clean-up
        self._running = False
        self._comm.set_terminate()
        self._comm_thread.join()

    def get_current_step(self):

        return self._image_i + 1

    def get_total_iterations(self):

        return self._images_total

    def get_progress(self):

        return float(self.get_current_step()) / self.get_total_iterations()

    def get_paused(self):

        return self._paused

    def set_terminate(self):

        self._running = False
        return True

    def set_pause(self):

        self._paused = True
        return True

    def set_unpause(self):

        self._paused = False
        return True

    def get_running(self):

        return self._running is not False

    def get_info(self):

        return ("__PREFIX__ {0}".format(self._model['experiment-prefix']),
                "__SCANNER__ No Scanner/Rebuilding",
                "__ROOT__ {0}\n".format(self._model['experiments-root']),
                "__1-PASS FILE__ {0}".format(self._output_path))

#
# RUN BEHAVIOR
#

if __name__ == "__main__":

    print "MAKE PROJECT WAS CALLED WITH:"
    print " ".join(sys.argv)
    print
    print

    parser = ArgumentParser(
        description="""The Make Project script compiles a new project
        as if it was run for the first time, but uses images allready
        existing.""")

    parser.add_argument("-i", "--input-file", type=str, dest="inputfile",
                        help="Settings File for the compilation",
                        metavar="PATH")

    parser.add_argument("-c", "--communications", type=str, dest="comm",
                        help="Communications file index", metavar="INDEX")

    parser.add_argument("-l", "--logging", type=str, dest="logging",
                        help="Logging level {0}".format(logging.getLevels()),
                        metavar="LOGGING LEVEL")

    args = parser.parse_args()

    if args.inputfile is None or not os.path.isfile(args.inputfile):

        parser.error("Could not find file {0}".format(args.inputfile))

    #LOGGING
    if (args.logging is not None and
            args.logging.lower() in logging.getLevels()):

        logging.setLogLevels(args.logging.lower())

    #Making the project
    mp = Make_Project(args.inputfile, args.comm)
    mp.run()