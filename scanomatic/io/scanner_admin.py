#!/usr/bin/env python
"""Resource for managing turning scanners on and off"""
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

import ConfigParser
from subprocess import Popen, PIPE
from enum import EnumMeta
from cPickle import loads, dumps

#
# INTERNAL DEPENDENCIES
#

import scanomatic.io.app_config as app_config
import scanomatic.io.paths as paths
import scanomatic.io.logger as logger
import scanomatic.io.power_manager as power_manager
import scanomatic.io.fixtures as fixtures


class Scanner_Manager(object):


    def __init__(self):

        self._logger = logger.Logger("Scanner Manager")
        self._conf = app_config.Config()
        self._paths = paths.Paths()
        self._fixtures = fixtures.Fixtures(self._paths, self._conf)

        self._scannerStatus = ConfigParser.ConfigParser(
            allow_no_value=True)
        try:
            self._scannerStatus.readfp(open(
                self._paths.rpc_scanner_status, 'r'))
        except IOError:
            self._logger.info(
                "No scanner statuses previously known, starting fresh")

        self._scannerConfs = ConfigParser.ConfigParser(
            allow_no_value=True)
        try:
            self._scannerConfs.readfp(open(
                self._paths.config_scanners, 'r'))
        except IOError:
            self._logger.info(
                "No specific scanner configurations, all asumed default")

        self._set_powerManagers()

    def __contains__(self, scanner):

        try:
            self._conf.get_scanner_socket(scanner)
        except KeyError:
            return False

        return True

    def __iter__(self):

        return iter(self._scannerStatus.sections())

    def _verifyDataStore(self, dataStore):

        if dataStore is None:
            dataStore = self._scannerStatus

        return dataStore

    def _verifySection(self, scanner, dataStore=None):

        dataStore = self._verifyDataStore(dataStore)

        if not dataStore.has_section(scanner):
            dataStore.add_section(scanner)

        return dataStore

    def _get(self, scanner, key, default=None, dataStore=None):
        
        dataStore = self._verifyDataStore(dataStore) 
        scanner = self._conf.get_scanner_name(scanner)
        self._verifySection(scanner, dataStore=dataStore)


        if dataStore.has_option(scanner, key):
            val = dataStore.get(scanner, key)
            if isinstance(val, EnumMeta):
                try:
                    val = loads(val)
                except:
                    self._logging.warning(
                        "Bad data for {0} on scanner {1} ({2})".format(
                            key, scanner, val))
            if val != '':
                return val

        return default 

    def _set(self, scanner, key, value, dataStore=None):

        dataStore = self._verifyDataStore(dataStore) 
        scanner = self._conf.get_scanner_name(scanner)
        self._verifySection(scanner, dataStore=dataStore)

        if value is None:
            dataStore.set(scanner, key, '')
        elif isinstance(value, bool):
            dataStore.set(scanner, key, str(int(value)))
        elif isinstance(value, EnumMeta):
            dataStore.set(scanner, key, dumps(value))
        else:
            dataStore.set(scanner, key, str(value))

    def _set_powerManagers(self):

        self._pm = dict()
        for i in range(1, self._conf.number_of_scanners + 1):
            self._pm[self._conf.get_scanner_name(i)] = self._conf.get_pm(i)


    def _get_alive_scanners(self):

        p = Popen(["scanimage", "-L", "|",
            "sed", "-n", "-E", r"s/^.*device[^\`]*.(.*libusb[^\`']*).*$/\1/p",
            ], shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        
        if 'no SANE devices' in stderr:
            return []
        else:
            #TODO: why map str?
            return [s for s in map(str, stdout.split('\n')) if len(s) > 0]

    def _get_recorded_statuses(self):

        claims = dict()

        for scanner in self._scannerStatus.sections():

            try:
                i = int(scanner[-1])
            except (ValueError, TypeError):
                self._logger.error(
                    "Scanner Status File has corrupt section '{0}'".format(
                        scanner))
                continue

            claims[i] = dict(
                    usb=self.getUSB(scanner, default=None),
                    power=bool(self._get(scanner, 'power', False)))

        for i in range(1, self._conf.number_of_scanners + 1):
            if i not in claims:
                claims[i] = dict(usb=None, power=False)

        return claims

    def _updateStatus(self, claim):

        for c in claim:

            self._set(c, 'usb', claim[c]['usb'])
            self._set(c, 'power', claim[c]['power'])
        self._save()

    def _save(self):

        self._scannerStatus.write(open(self._paths.rpc_scanner_status, 'w'))

    def _rescue(self, usbList, claim):

        power = list(self.powerStatus)
        offs = 0

        for i in range(1, self._conf.number_of_scanners + 1):

            if power[i] and claim[i]['usb'] in usbList or not claim[i]['usb']:
                self.requestOff(i, updateClaim=False)
                power[i] = False
                offs += 1
                claim[i] = dict(usb=None, power=False)

        self._updateStatus(claim)

    def _match_scanners(self, scannerList):

        claim = self._get_recorded_statuses()
        noFounds = []
        while scannerList:
            usb = scannerList.pop()
            found = False
            for c in claim:
                if claim[c]['usb'] and claim[c]['usb'] == usb:
                    claim[c]['matched'] = True
                    found = True
                    break

            if not found:

                noFounds.push(usb)

        if len(noFounds) > 1:
            self._critical("More than one unclaimed scanner")
            self._rescue(noFounds, claim)
            return False

        for usb in noFounds:

            found = False
            for c in claim:

                if claim[c]['power'] and not claim[c]:

                    if not found:
                        claim[c]['usb'] = usb
                        found = True
                    else:
                        self._logger.critical(
                            "More than one scanner claiming to" +
                            "be on without matched usb")
                
                        self._rescue(noFounds, claim)
                        return False
                    
        self._updateStatus(claim)

        return sum(1 for c in claim 
                   if 'matched' in claim[c] and claim[c]['matched']) == \
               sum(1 for c in claim
                   if 'usb' in claim[c] and claim[c]['usb'])

    def _get_power_type(self, scanner):

        return self._get(scanner, 'powerType',
                         default='SIMPLE', dataStore=self._scannerConfs)
        
    def isOwner(self, scanner, jobID):

        owner = self._get(scanner, 'jobID')
        return owner is not None and owner == jobID

    def requestOn(self, scanner, jobID):

        if self.sync():

            if self.getUSB(scanner, default=False):
                #Scanner is already On and connected
                return True

            if not self.isOwner(scanner, jobID):
                self._logger.error("Can't turn on, owner missmatch")
                return False

            self._set(scanner, 'usb', None)

            success = self._pm[scanner].powerUpScanner()

            self._set(scanner, 'power', sucess)

            self._save()
            return success

        else:

            return False

    def requestOff(self, scanner, jobID, updateClaim=True):

        if not self.isOwner(scanner, jobID):
            self._logger.error("Can't turn on, owner missmatch")
            return False

        success = self._pm[scanner].powerDownScanner()

        if success and updateClaim:
            self._set(scanner, 'usb', None)
            self._set(scanner, 'power', False)

            self._save()

        return success 

    def requestClaim(self, scanner, pid, jobID):

        if scanner > self._conf.number_of_scanners:
            return False
        
        sName = self._conf.get_scanner_name(scanner)

        try:
            ownerProc = int(self._get(scanner, 'pid', -1))
        except (ValueError, TypeError):
            ownerProc = -1

        if ownerProc > 0 and pid != ownerProc:

            if psutil.pid_exists(ownerProc):

                self._logger.warning("Trying to claim {0} when claimed".format(
                    sName))
                return False

            else:
                self._logger.info(
                    "Releasing {0} since owner process is dead".format(
                        sName))

                self.releaseScanner(scanner)

        if self._get(scanner, "jobID", None):
            self._logger.warning("Overwriting previous jobID for {0}".format(
                sName))

        self._set(scanner, "pid", pid)
        self._set(scanner, "jobID", jobID)
        self._save()
        return True

    def releaseScanner(self, scanner):

        if self.getUSB(scanner, default=False):
            self.requestOff(scanner)
        self._set(scanner, "pid", None)
        self._set(scanner, "jobID", None)
        self._save()
        return True

    def owner(self, scanner):

        return (int(self._get(scanner, "pid", None)),
                self._get(scanner, "jobID", None))
        
    def isOwner(self, scanner, jobID):

        return jobID is not None and self._get(scanner, "jobID", None) == jobID

    def updatePid(self, jobID, pid):

        if jobID is None or not isinstance(pid, int) and pid < 1:
            return False

        for scanner in self._scannerStatus.sections():
            job = self._get(scanner, "jobID", None)
            if job == jobID:
                self._set(scanner, "pid", pid)
                self._save()
                return True

        return False

    def getUSB(self, scanner, jobID=None, default=''):
        """Gets the usb that a scanner is connected on.
        """
        
        """
        if jobID is None or jobID != self._get(scanner, "jobID", None):
            self._logger.warning("Incorrect jobID for scanner {0}".format(
                scanner))
            return False
        """
        
        if not self._get(scanner, "power", False):

            return default

        return self._get(scanner, "usb", default)

    def getPower(self, scanner):

        return bool(int(self._get(scanner, "power", 0)))

    def sync(self):

        return self._match_scanners(self._get_alive_scanners())

    def fixtureExists(self, fixtureName):

        return fixtureName in self._fixtures

    def getFixtureNames(self):

        return self._fixtures.get_names()

    def getStatus(self, scanner):

        return dict(
            name=self._conf.get_scanner_name(scanner),
            pid=self._get(scanner, "pid", ""),
            power=self.getPower(scanner),
            owner=self._get(scanner, "jobID", ""),
            usb=self.getUSB(scanner))

    @property
    def powerStatus(self):
        return (self._pm[i].status() for i in 
                range(1, self._conf.number_of_scanners + 1))
