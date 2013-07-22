#!/usr/bin/env python3

# prpr_human.py, a part of PR-PR (previously known as PaR-PaR), a biology-friendly language for liquid-handling robots
# Author: Nina Stawski, nstawski@lbl.gov, me@ninastawski.com
# Copyright 2012-2013, Lawrence Berkeley National Laboratory
# http://github.com/JBEI/prpr/blob/master/license.txt

__author__ = 'Nina Stawski'
__version__ = '0.6'

import os
from prpr import *

class PRPR:
    wash = 'Wash or change the tips.'
    def __init__(self, ID):
        self.expID = ID
        db = DatabaseHandler(ID)
        self.transfers = db.transfers
        self.logger = []
        self.robotConfig = []
        self.transactions = []
        self.volumesList = []
        self.createTransfer()
        self.updateTransactions()
        self.addWash()
        self.saveLog()
        self.saveConfig()

    def createTransfer(self):
        allTransfers = self.transfers
        print('allTransfers', allTransfers)
        for transfer in allTransfers:
            print('transffffferrrr', transfer)
            trType = transfer['type']
            els = transfer['info']
            if trType == 'transfer':
                self.constructTransaction(('Aspirate', 'Dispense'), els)

            elif trType == 'command':
                self.parseCommand(els)

    def checkIfWellsAreConsequent(self, well1Info, well2Info):
        if well1Info['plate'] == well2Info['plate']:
            well1 = well1Info['well']
            well2 = well2Info['well']
            if int(well1[1]) == int(well2[1]):
                if int(well1[0]) == (int(well2[0]) - 1):
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

    def config(self, line):
        self.robotConfig.append(line)

    def addWash(self):
        if not len(self.robotConfig):
            self.config(self.wash)
        else:
            if not self.robotConfig[-1].startswith('Wash'):
                self.config(self.wash)

    def saveConfig(self):
        def writeLines(file):
            for line in self.robotConfig:
                file.write(line.rstrip() + '\r\n')
                
        fileName = ''
        for key in defaults.fileExtensions:
            file_ = 'esc' + os.sep + 'config' + self.expID + '.' + defaults.fileExtensions[key]
            if os.path.isfile(file_):
                fileName = file_
        with open(fileName, 'a', encoding='latin1') as myfile:
            writeLines(myfile)

    def log(self, item):
        from datetime import datetime
        time = str(datetime.now())
        self.logger.append(time + ': ' + item)

    def saveLog(self):
        logname = 'logs/experiment' + self.expID + '.log'
        self.log('Translation log location: ' + logname)
        writefile = open(logname, "a")
        writefile.writelines( "%s\n" % item for item in self.logger )
        print('Translation log location: ' + logname)

    def message(self, message):
        self.addWash()
        command = '# ' + message
        self.config(command)

    def comment(self, comment):
        command = '# ' + comment
        self.config(command)

    def mix(self, tipNumber, volumesString, gridAndSite, wellString, mixOptions):
        location = str(gridAndSite[0]) + ',' + str(gridAndSite[1])
        command = 'Mix(' + str(tipNumber) + ',"LCWMX",' + \
                  volumesString + ',' + location + ',1,"' + \
                  wellString + '",' + mixOptions + ',0);'
        self.config(command)

    def command(self, action, tipNumber, gridAndSite, wellString, method, volumesString):
        location = str(gridAndSite[0]) + ',' + str(gridAndSite[1])
        command = action            + '(' + \
                  str(tipNumber)    + ',"' + \
                  method            + '",' + \
                  volumesString     + ',' + \
                  location          + ',1,"' + \
                  wellString        + '",0);'
        self.config(command)

    def updateTransactions(self):
        for transaction in self.transactions:
            print('updateTransactions. transaction', transaction)
            #empty containers for volumes, plate info and wells are created
            volumesDict = {}
            wells = []
            plateInfo = {}
            for t in transaction:
                if t:
                    for e in range(0, len(t)):
                        element = t[e]
                        if element['command'] == 'message':
                            self.message(element['message'])
                        elif element['command'] == 'comment':
                            self.comment(element['message'])
                        else:
                            if e:
                                previousElement = t[e-1]
                                consequent = self.checkIfWellsAreConsequent(previousElement['wellInfo'], element['wellInfo'])
                                if not consequent:
                                    volumesList = self.fillVolumesList(volumesDict)
                                    volumesLine = self.joinVolumesList(volumesList)
                                    plateDimensions = plateInfo['dimensions']
                                    wellenc = self.getWellEncoding(wells, plateDimensions)
                                    gridAndSite = plateInfo['location']
                                    volume = volumesLine[0]
                                    tipsEncoding = volumesLine[1]
                                    action = previousElement['command']
                                    if action == 'Aspirate' or action == 'Dispense':
                                        method = element['method']
                                        self.command(action, tipsEncoding, gridAndSite, wellenc, method, volume)
                                    if action == 'Mix':
                                        mixOptions = element['times']
                                        self.mix(tipsEncoding, volume, gridAndSite, wellenc, mixOptions)

                                    volumesDict = {element['tipNumber'] : '"' + str(element['volume']) + '"' }
                                    wells = [element['wellInfo']['well']]
                                    volumesDict[element['tipNumber']] = '"' + str(element['volume']) + '"'
                                    plateInfo = {'dimensions' : element['wellInfo']['plateDimensions'], 'location' : element['wellInfo']['plate']}
                                else:
                                    volumesDict[element['tipNumber']] = '"' + str(element['volume']) + '"'
                                    wells.append(element['wellInfo']['well'])
                            else:
                                if element['command'] == 'Aspirate' or element['command'] == 'Mix':
                                    self.addWash()
                                volumesDict[element['tipNumber']] = '"' + str(element['volume']) + '"'
                                wells.append(element['wellInfo']['well'])
                                plateInfo = {'dimensions' : element['wellInfo']['plateDimensions'], 'location' : element['wellInfo']['plate']}
                    element = t[len(t)-1]

                    if element['command'] == 'message' or element['command'] == 'comment':
                        pass
                    else:
                        volumesList = self.fillVolumesList(volumesDict)
                        volumesLine = self.joinVolumesList(volumesList)
                        plateDimensions = plateInfo['dimensions']
                        wells.append(element['wellInfo']['well'])
                        wellenc = self.getWellEncoding(wells, plateDimensions)
                        gridAndSite = plateInfo['location']
                        volume = volumesLine[0]
                        tipsEncoding = volumesLine[1]
                        action = element['command']
                        if action == 'Aspirate' or action == 'Dispense':
                            method = element['method']
                            self.command(action, tipsEncoding, gridAndSite, wellenc, method, volume)
                        if action == 'Mix':
                            mixOptions = element['times']
                            self.mix(tipsEncoding, volume, gridAndSite, wellenc, mixOptions)

    def constructTransaction(self, commandsList, transferList):
        """
        Creating the aspirate / dispense strings from the list of transfers
        """

        trList = {'Aspirate' :  [], 'Dispense' :  []}
        tr = transferList
        for command in commandsList:
            for e in tr:
                method = e['method']
                if command == 'Aspirate':
                    wellInfo = e['source']
                elif command == 'Dispense':
                    wellInfo = e['destination']
                    
                print('e_volume', e['volume'])

                trList[command].append({ 'command' : command, 'wellInfo' : wellInfo, 'volume' : e['volume'][2], 'method' : method })

        aspirate = trList['Aspirate']
        dispense = trList['Dispense']

        for el in range (0, len(aspirate)):
            for l in range(0, len(aspirate[el])):
                aspirate[el][l]['tipNumber'] = l + 1
                dispense[el][l]['tipNumber'] = l + 1
            self.transactions.append([aspirate[el] + dispense[el]])

    def parseCommand(self, transferList):
        tr = transferList
        trList = []
        for option in tr:
            if option['command'] == 'mix':
                wellInfo = option['target']
                trList.append({ 'command' : 'Mix', 'wellInfo' : wellInfo})
            elif option['command'] == 'message' or option['command'] == 'comment':
                trList.append(option)
        self.transactions.append(trList)

    def createMixString(self, volumesString, newVolume):
        ms = volumesString.split(',')
        for i in range(0, len(ms)):
            if ms[i] != '0':
                ms[i] = '"' + newVolume + '"'
        volumesString = self.joinVolumesList(ms)
        return volumesString[0]

    def fillVolumesList(self, volumes):
        """
        Finalizes the list of volumes by adding zeroes where needed.
        volumes - current list of volumes
        """
        for l in range (0, 12):
            if l+1 not in volumes:
                volumes[l+1] = '0'
        volumesList = []
        for d in range (1, 13):
            volumesList.append(volumes[d])
        return volumesList

    def joinVolumesList(self, volumesList):
        """
        Creates the final list of volumes for aspirate / dispense commands
        volumesList - list of volumes to join
        """
        tipsEnc = 0
        for i in range(0, len(volumesList)):
            if volumesList[i] != '0':
                tipsEnc += self.getTipEncoding(i+1)
        volumesString = ','.join(volumesList)
        return volumesString, tipsEnc
    
class defaults:
    fileExtensions = {'txt' : 'txt'}

if __name__ == '__main__':
    prpr = Prpr_Tecan(310)
    print('Config:')
    for element in prpr.robotConfig:
        print(element)