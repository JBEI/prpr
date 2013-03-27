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
        print('locations::', self.mfWellLocations)
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
            trNum = str(transferNumber) + str(t) + 't'
            config['name'] = 'transfer' + trNum
            config['details'] = ['transfer' + trNum]
            source = transfer['source']['well']
            destination = transfer['destination']['well']
            wait = transfer['wait']
            config['times'] = int(transfer['times'])
            transferPath = self.findPath(source, destination, [source])
            p = 0
            while p < len(transferPath) - 1:
                openWell = transferPath[p + 1]
                currentWell = transferPath[p]
                closeWell = transferPath[p - 1]
                if p == 0 and len(self.mfWellConnections[closeWell]) == 1:
                    config['details'].append('o' + currentWell)
                    config['details'].append('o' + openWell)
                    config['details'].append('call wait' + trNum)
                    global p
                    p = 1
                    openWell = transferPath[p + 1]
                    closeWell = transferPath[p - 1]
                config['details'].append('c' + closeWell)
                config['details'].append('o' + openWell)
                config['details'].append('call wait' + trNum)
                if p == (len(transferPath) - 2) and len(self.mfWellConnections[openWell]) == 1:
                    config['details'].append('c' + currentWell)
                    config['details'].append('c' + openWell)
                    config['details'].append('call wait' + trNum)
                p += 1
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


    def findPath(self, source, destination):
        """
        Finds a shortest path between two wells on a microfluidic table.
        
        :param source: source well, int (must be in self.mfWellConnections)
        :param destination: destination well, int (must be in self.mfWellConnections)
        :return: resulting path, list
        
        """
        
        def searchBranch(path, source, destination):
            for connection in self.mfWellConnections[source]:
                newPath = deepcopy(path)
                newPath.append(connection)
                if connection == destination:
                    return newPath
                else:
                    searchBranch(newPath, connection, destination)
        
        connections = {}
        path = []
        destX = self.mfWellLocations[destination][0]
        destY = self.mfWellLocations[destination][1]
        for connection in self.mfWellConnections[source]:
            x = self.mfWellLocations[connection][0]
            y = self.mfWellLocations[connection][1]
            checksum = abs(destX - x) + abs(destY - y)
            if connection not in path:
                connections[connection] = checksum
        result = min(connections, key=connections.get)
        print(result)
        path.append(result)
        if result == destination:
            return path
        else:
            path = self.findPath(result, destination, path)
            return path


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