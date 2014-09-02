"""The master effector of the analysis, calls and coordinates image analysis
and the output of the process"""
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

import md5
import time
import ConfigParser
from operator import itemgetter
import collections

#
# INTERNAL DEPENDENCIES
#

import scanomatic.io.paths as paths
import scanomatic.io.logger as logger

#
# CLASSES
#


class Queue(object):

    TYPE_REBUILD_PROJECT = 0
    TYPE_IMAGE_ANALSYS = 1
    TYPE_FEATURE_EXTRACTION = 2

    def __init__(self):

        self._paths = paths.Paths()
        self._logger = logger.Logger("RPC Subproc Queue")
        self._queue = ConfigParser.ConfigParser()
        try:
            self._queue.readfp(open(self._paths.rpc_queue))
        except IOError:
            self._logger.info("No queue existing, creating new empy")
            self._queue.write(open(self._paths.rpc_queue, 'w'))

    def __nonzero__(self):

        return self._queue.sections() != []

    def writeUpdates(self):

        self._queue.write(open(self._paths.rpc_queue, 'w'))

    def setPriority(self, subProcId, priority, writeOnUpdate=True):

        try:
            self._queue.set(subProcId, "priority", str(priority))
        except ConfigParser.NoSectionError:
            self._logger.error("The subproc id {0} does not exist".format(
                subProcId))
            return False

        if writeOnUpdate:
            self.writeUpdates()

        return True

    def remove(self, subProcId):

        try:
            self._queue.remove_section(subProcId)
        except ConfigParser.NoSectionError:
            self._logger.error("The subproc id {0} is unknown".format(
                subProcId))
            return False

        self.writeUpdates()

        return True

    def getJobInfo(self, jobId):

        try:
            return (jobId, self._queue.get(jobId, "label"),
                    self._queue.getint(jobId, "priority"))
        except:
            self._logger.warning(
                "Problem extracting info on job {0}, '{1}'".format(
                    jobId,
                    ["No queue", "Id not in queue", "No label",
                     "No prio", "Other"][
                         self._queue is None and 0 or
                         self._queue.has_section(jobId) is False and 1 or
                         self._queue.has_option(jobId, "label") is False and 2
                         or self._queue.has_option(jobId, "priority") is False
                         and 3 or 4]))
            return None

    def getJobsInQueue(self):

        l = [self.getJobInfo(j) for j in self._queue.sections()]
        return sorted([i for i in l if i is not None], key=itemgetter(2),
                      reverse=True)

    def popHighestPriority(self):

        prioSection = None
        highestPrio = -1

        for s in self._queue.sections():

            if not self._queue.has_option(s, "priority"):

                self.setPriority(s, 0, writeOnUpdate=False)

            prio = self._queue.getint(s, "priority")
            if (prio > highestPrio):
                if (prioSection is not None):
                    self.setPriority(prioSection, highestPrio + 1,
                                     writeOnUpdate=False)

                highestPrio = prio
                prioSection = s
            else:
                self.setPriority(prioSection, prio + 1)

        if prioSection is not None:

            procInfo = {'id': prioSection}
            if (self._queue.has_option(prioSection, "label")):
                procInfo['label'] = self._queue.get(prioSection, "label")
            else:
                procInfo['label'] = ""

            if (self._queue.has_option(prioSection, "type")):
                procInfo['type'] = self._queue.getint(prioSection, "type")
            else:
                procInfo['type'] = None

            if (self._queue.has_option(prioSection, "args")):
                try:
                    procInfo['args'] = eval(
                        self._queue.get(prioSection, "args"))
                    iter(procInfo['args'])
                except (TypeError, SyntaxError):
                    procInfo['args'] = tuple()
            else:
                procInfo['args'] = tuple()

            if (self._queue.has_option(prioSection, "kwargs")):

                try:
                    procInfo['kwargs'] = eval(
                        self._queue.get(prioSection, "kwargs"))
                except SyntaxError:
                    procInfo['kwargs'] = dict()

                if not isinstance(procInfo['kwargs'], collections.Mapping):

                    procInfo['kwargs'] = dict()

            else:
                procInfo['kwargs'] = dict()

            self.remove(prioSection)
            self.writeUpdates()
            return procInfo

        return None

    def add(self, subprocType, jobLabel, priority=None, *args, **kwargs):

        if (subprocType not in [getattr(self, p) for p in dir(self) if
                                p.startswith("TYPE_")]):

            self._logger.error("Unknown subprocess type ({0})".format(
                subprocType))
            return None

        if priority is None:
            priority = subprocType

        goodName = False

        while not goodName:
            subprocId = md5.new(str(time.time())).hexdigest()
            try:
                self._queue.add_section(subprocId)
                goodName = True
            except ConfigParser.DuplicateSectionError:
                pass

        self._queue.set(subprocId, "type", str(subprocType))
        self._queue.set(subprocId, "label", str(jobLabel))

        self.setPriority(subprocId, priority, writeOnUpdate=False)

        self._queue.set(subprocId, "args", str(args))
        self._queue.set(subprocId, "kwargs", str(kwargs))

        self.writeUpdates()

        return subprocId
