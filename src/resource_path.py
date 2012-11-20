#!/usr/bin/env python
"""Resource Paths"""
__author__ = "Martin Zackrisson"
__copyright__ = "Swedish copyright laws apply"
__credits__ = ["Martin Zackrisson"]
__license__ = "GPL v3.0"
__version__ = "0.997"
__maintainer__ = "Martin Zackrisson"
__email__ = "martin.zackrisson@gu.se"
__status__ = "Development"

#
# DEPENDENCIES
#

import os

#
# CLASSES
#


class Paths(object):

    def __init__(self, program_path, config_file=None):

        #DIRECTORIES
        self.root = program_path
        self.src = self.root + os.sep + "src"
        self.config = self.src + os.sep + "config"
        self.fixtures = self.config + os.sep + "fixtures"
        self.images = self.src + os.sep + "images"

        #RUN-files
        self.scanomatic = self.root + os.sep + "run_scan_o_matic.py"
        self.analysis = self.src + os.sep + "analysis.py"
        self.experiment = os.sep.join((self.root, "run_experiment.py"))

        #IMAGES
        self.marker = self.images + os.sep + "orientation_marker_150dpi.png" 

        #LOG
        self.log = self.root + os.sep + "log"
        self.log_scanner_out = os.sep.join((self.log, "scanner_{0}.stdout"))
        self.log_scanner_err = os.sep.join((self.log, "scanner_{0}.stderr"))

        #EXPERIMENT
        self.experiment_root = os.path.expanduser("~") + os.sep + "Documents"
        self.experiment_analysis_relative_path = "analysis"
        self.experiment_analysis_file_name = "analysis.log"
        self.experiment_first_pass_analysis_relative = "{0}.1_pass.analysis"
        self.experiment_first_pass_log_relative = ".1_pass.log"

        #LOCK FILES
        self.lock_root = os.sep.join((os.path.expanduser("~"), ".scan_o_matic"))
        self.lock_power_up_new_scanner = self.lock_root + ".new_scanner.lock"
        self.lock_scanner_pattern = self.lock_root + ".scanner.{0}.lock"
