__author__ = 'Nina Stawski'
__contact__ = 'me@ninastawski.com'

#microfluidics support for PRPR

import os
from prpr import *
from copy import deepcopy

class Prpr_MF:
    def __init__(self, ID):
        self.expID = ID
        db = DatabaseHandler(ID)
        self.transfers = db.transfers
        self.mfWellConnections = db.mfWellConnections
        self.mfWellLocations = db.mfWellLocations
        self.logger = []
        self.robotConfig = []
        self.transactions = []
        self.volumesList = []
        self.createTransfer()
        self.saveLog()
        self.saveConfig()

    def createTransfer(self):
        allTransfers = self.transfers
        unparsedTransfers = []
        for i, transfer in enumerate(allTransfers):
            print('transfer__', transfer)
            trType = transfer['type']
            els = transfer['info']
            if trType == 'command':
                self.parseCommand(els)
            elif trType == 'transfer':
                transfers = self.parseTransfer(els, i)
                for element in transfers:
                    unparsedTransfers.append(element)
        self.saveTransfers(unparsedTransfers)

    def parseTransfer(self, transferList, transferNumber):
        transfers = []
        for t, transfer in enumerate(transferList):
            config = {}
            trNum = str(transferNumber) + str(t)
            config['name'] = 'transfer' + trNum
            config['details'] = ['transfer' + trNum]
            source = transfer['source']['well']
            destination = transfer['destination']['well']
            wait = transfer['wait']
            config['times'] = int(transfer['times'])
            transferPath = self.findPath(source, destination)
            for p in range(0, len(transferPath) - 1):
                openWell = transferPath[p + 1]
                closeWell = transferPath[p]
                if p == 0 and len(self.mfWellConnections[closeWell]) == 1:
                    config['details'].append('o' + closeWell)
                    config['details'].append('call wait' + trNum)
                config['details'].append('o' + openWell)
                config['details'].append('c' + closeWell)
                config['details'].append('call wait' + trNum)
                if p == (len(transferPath) - 2) and len(self.mfWellConnections[openWell]) == 1:
                    config['details'].append('c' + openWell)
                    config['details'].append('call wait' + trNum)
            config['details'].append('end')
            config['wait'] = ['wait' + trNum, 'w' + str(wait), 'end']
            print('confing)))', config)
            transfers.append(config)
        return transfers

    def saveTransfers(self, transferList):
        self.config('main')
        for name, times in ((t['name'], t['times']) for t in [transfer for transfer in transferList]):
            self.config('call ' + name + (' ' + str(times) if times > 1 else ''))
        self.config('end')
        self.config('')
        for transaction in (tr['details'] for tr in transferList):
            for line in transaction:
                self.config(line)
            self.config('')
        for wait in (tr['wait'] for tr in transferList):
            for line in wait:
                self.config(line)
            self.config('')


    def findPath(self, well1, well2):
        def isConnected(srcWell, dstWell):
            if dstWell in self.mfWellConnections[srcWell]:
                return True
            else:
                return False

        def returnPath(paths, previousPath, currentWell, destinationWell):
            if len(paths) == len(self.mfWellConnections)*5: return min(paths, key=len) #to shorten the wait time for the config until I optimize the code
            print(currentWell, destinationWell, '!!')
            if destinationWell in self.mfWellConnections[currentWell]:
                previousPath.append(destinationWell)
                paths.append(previousPath)
            else:
                for well in self.mfWellConnections[currentWell]:
                    currentPath = deepcopy(previousPath)
                    if well not in currentPath:
                        currentPath.append(well)
                        if isConnected(well, destinationWell):
                            currentPath.append(destinationWell)
                            paths.append(currentPath)
                        else:
                            for i in range(0, len(self.mfWellConnections[well])):
                                cWell = self.mfWellConnections[well][i]
                                if len(self.mfWellConnections[cWell]) > 1:
                                    if cWell not in currentPath:
                                        newPath = deepcopy(currentPath)
                                        newPath.append(cWell)
                                        returnPath(paths, newPath, cWell, destinationWell)
            print('mf_paths', paths)
            return min(paths, key=len) #returning the best path in terms of length
        paths = returnPath([], [well1], well1, well2)
        return paths


    def parseCommand(self, transferList):
        print('transferList', transferList)
        trList = []
        for option in transferList:
            if option['command'] == 'message' or option['command'] == 'comment':
                trList.append(option)
                self.transactions.append(trList)


    def config(self, line):
        self.robotConfig.append(line)


    def saveConfig(self):
        fileName = 'esc' + os.sep + 'config' + self.expID + '.mf'
        myfile = open(fileName, 'a')
        for line in self.robotConfig:
            myfile.write(line.rstrip() + '\r\n')
        myfile.close()


    def log(self, item):
        from datetime import datetime

        time = str(datetime.now())
        self.logger.append(time + ': ' + item)


    def saveLog(self):
        logName = 'logs/experiment' + self.expID + '.log'
        self.log('Translation log location: ' + logName)
        writefile = open(logName, "a")
        writefile.writelines("%s\n" % item for item in self.logger)
        print('Translation log location: ' + logName)