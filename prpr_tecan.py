#!/usr/bin/env python3

# prpr_tecan.py, a part of PR-PR (previously known as PaR-PaR), a biology-friendly language for liquid-handling robots
# Author: Nina Stawski, nstawski@lbl.gov, me@ninastawski.com
# Copyright 2012-2013, Lawrence Berkeley National Laboratory
# http://github.com/JBEI/prpr/blob/master/license.txt

__author__ = 'Nina Stawski'
__version__ = '0.6'

import os
from prpr import *

class PRPR:
    # wash = 'Wash(255,1,1,1,0,"2",500,"1.0",500,20,70,30,1,1,1000);'
    wash = 'Wash(255,17,1,17,2,"2.0",500,"1.0",500,10,70,30,0,0,1000);'
    def __init__(self, ID):
        self.expID = ID
        db = DatabaseHandler(ID)
        self.transfers = db.transfers
        self.maxTips = db.maxTips
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
        for transfer in allTransfers:
            trType = transfer['type']
            els = transfer['info']
            if trType == 'transfer':
                self.constructTransaction(('Aspirate', 'Dispense'), els)

            elif trType == 'command':
                self.parseCommand(els)

    def getTipEncoding(self, tipNumber):
        return 1 << (tipNumber - 1)

    def getTipAmountString(self, tipNumber, amount):
        param = ""
        for i in range(1,13):
            if i <= tipNumber:
                param += '"' + str(amount) + '",'
            elif (not i) == 12:
                param += ","
            else:
                param += "0,"
        return param

    def getWellEncoding(self, wellsList, maximums):
        maxRows = maximums[0]
        maxColumns = maximums[1]
        header = '{0:02X}{1:02X}'.format(maxColumns, maxRows)
        selString = bytearray()
        bitCounter = 0
        bitMask = 0
        for x in range(1, maxColumns + 1):
            for y in range(1, maxRows + 1):
                for (row, column) in wellsList:
                    if x == column and y == row:
                        bitMask |= 1 << bitCounter
                bitCounter += 1
                if bitCounter > 6:
                    selString.append(0x30 + bitMask)
                    bitCounter = 0
                    bitMask = 0
        if bitCounter > 0:
            selString.append(0x30 + bitMask)
        return header + selString.decode('latin1')

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
        command = 'UserPrompt("' + message + '",0,-1);'
        self.config(command)

    def comment(self, comment):
        command = 'Comment("' + comment + '");'
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

        totalTips = sum([x['volume'][1] for x in transferList])
        trsNeeded = totalTips / self.maxTips
        trs = 1
        if trsNeeded > 1:
            trs = int(trsNeeded) + 1

        trList = {'Aspirate' : [[] for n in range(0, max([x['volume'][1] + 1 for x in transferList]))], 'Dispense' :  [[] for n in range(0, max([x['volume'][1] + 1 for x in transferList]))]}
        tr = self.splitTransaction(transferList)
        for element in tr:
            for command in commandsList:
                tipNumber = 1
                for e in element:
                    method = e['method']
                    if command == 'Aspirate':
                        wellInfo = e['source']
                    elif command == 'Dispense':
                        wellInfo = e['destination']

                    for x in range(0, e['volume'][1]):
                        trList[command][x].append({ 'command' : command, 'wellInfo' : wellInfo, 'volume' : e['volume'][0], 'method' : method }) #, 'tipNumber' : tip

                    if len(e['volume']) == 3:
                        trList[command][e['volume'][1]].append({ 'command' : command, 'wellInfo' : wellInfo, 'volume' : e['volume'][2], 'method' : method })

        aspirate = self.splitTransaction([j for i in trList['Aspirate'] for j in i])
        dispense = self.splitTransaction([j for i in trList['Dispense'] for j in i])

        for el in range (0, len(aspirate)):
            for l in range(0, len(aspirate[el])):
                aspirate[el][l]['tipNumber'] = l + 1
                dispense[el][l]['tipNumber'] = l + 1
            self.transactions.append([aspirate[el] + dispense[el]])

    def parseCommand(self, transferList):
        tr = self.splitTransaction(transferList)
        for element in tr:
            elements = []
            el = self.splitTransaction(element)
            for e in el:
                trList = []
                tipNumber = 1
                for option in e:
                    if option['command'] == 'mix':
                        wellInfo = option['target']
                        trList.append({ 'command' : 'Mix', 'tipNumber' : tipNumber, 'wellInfo' : wellInfo, 'volume' : option['volume'], 'times' : option['times'] })
                        tipNumber += 1
                    elif option['command'] == 'message' or option['command'] == 'comment':
                        trList.append(option)
                elements.append(trList)
            self.transactions.append(elements)

    def splitTransaction(self, transferList):
#        count = 1
        list = []
        for t in range(0, len(transferList), self.maxTips):
            cutList = transferList[t:t+self.maxTips]
            list.append(cutList)
        return list

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
    
    # @staticmethod
    # def parseLocation(self, location):
    #     """
    #     Parses the given location, i.e. PL3:A1+4 to individual wells
    #     """
    # 
    #     def ParseWells(wells, plateDimensions):
    #         wellsLargeList = wells.split(',')
    #         wellsNewlist = []
    #         print('wells, wellslargelitt', wells, wellsLargeList)
    #         for well in wellsLargeList:
    #             wellsList = well.split('+')
    #             direction = 'vertical'
    #             if '-' in well:
    #                 wellsList = well.split('-')
    #                 direction = 'horizontal'
    #             elif '~' in well:
    #                 tempWellsList = well.split('~')
    #                 startWellCoords = GetWellCoordinates(tempWellsList[0], plateDimensions, str(location))
    #                 endWellCoords = GetWellCoordinates(tempWellsList[1], plateDimensions, str(location))
    #                 wellsAmount = (endWellCoords[0] - startWellCoords[0]) * plateDimensions[0] + endWellCoords[1] - startWellCoords[1] + 1
    #                 print('(', endWellCoords[0], '-', startWellCoords[0], ') *', plateDimensions[0], '-', endWellCoords[1], '+', startWellCoords[1])
    #                 print(startWellCoords, endWellCoords, plateDimensions, wellsAmount)
    #                 wellsList = (tempWellsList[0], wellsAmount)
    #                 direction = 'vertical'
    #             if wellsList[0]:
    #                 startWell = wellsList[0]
    #                 rowsMax = plateDimensions[0]
    #                 colsMax = plateDimensions[1]
    #                 if len(wellsList) == 2:
    #                     assert (wellsList[1] != ''), "Well number after '+' can't be empty."
    #                     numberWells = int(wellsList[1])
    #                     startCoords = GetWellCoordinates(startWell, plateDimensions, str(location))
    #                     for i in range(0, numberWells):
    #                         addedWells = WellsRename(startCoords, i, plateDimensions, direction)
    #                         assert(addedWells[1] <= colsMax), 'Wells locations are out of range'
    #                         wellsNewlist.append(addedWells)
    #                 elif len(wellsList) == 1:
    #                     wellsNewlist.append(GetWellCoordinates(wellsList[0], plateDimensions, str(location)))
    #                 else:
    #                     self.errorLog('Error. Can\'t be more than one \'+\'. Correct syntax in ' + str(location) + ' and run again. \n')
    #             else:
    #                 self.errorLog('Error. Well can\'t be empty in locaton "' + str(location) + '"')
    # 
    #         return wellsNewlist
    # 
    #     def WellsRename(startCoords, i, plateDimensions, direction):
    #         rowsMax = plateDimensions[0]
    #         colsMax = plateDimensions[1]
    #         currentNum = startCoords[0] + i
    #         if direction == 'vertical':
    #             if currentNum <= rowsMax:
    #                 newCol = startCoords[1]
    #                 return currentNum, newCol
    #             elif currentNum > rowsMax:
    #                 times = int(currentNum / rowsMax)
    #                 newCol = startCoords[1] + times
    #                 newRow = currentNum - (times * rowsMax)
    #                 if newRow == 0:
    #                     return newRow + rowsMax, newCol - 1
    #                 else:
    #                     return newRow, newCol
    #         if direction == 'horizontal':
    #             if currentNum <= colsMax:
    #                 newRow = startCoords[1]
    #                 return newRow, currentNum
    #             elif currentNum > colsMax:
    #                 times = int(currentNum / colsMax)
    #                 newRow = startCoords[1] + times
    #                 newCol = currentNum - (times * colsMax)
    #                 if newCol == 0:
    #                     return newRow - 1, newCol + colsMax
    #                 else:
    #                     return newRow, newCol
    # 
    # 
    #     def GetWellCoordinates(well, plateDimensions, location):
    #         """
    #         Takes the well coordinates entered by the user and dimensions of the plate and returns the wells plate coordinates
    #         """
    #         if well:
    #             rowsMax = plateDimensions[0]
    #             colsMax = plateDimensions[1]
    #             try:
    #                 int(well)
    #                 well = int(well)
    #                 if well > rowsMax * colsMax:
    #                     self.errorLog('Error. Well "' + str(well) + '" in location "' + location + '" is out of range')
    #                 else:
    #                     if well <= rowsMax:
    #                         newCol = 1
    #                         newRow = well
    #                     else:
    #                         times = int(well / rowsMax)
    #                         newCol = times + 1
    #                         newRow = well - (times * rowsMax)
    #                     if newRow == 0:
    #                         return newRow + rowsMax, newCol - 1
    #                     else:
    #                         return newRow, newCol
    #             except ValueError:
    #                 alphabet = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'
    #                 letterIndex = alphabet.find(well[:1]) + 1
    #                 if letterIndex > rowsMax:
    #                     self.errorLog('Error. Well "' + well + '" letter coordinate in location "' + location + '" is out of range')
    #                 elif int(well[1:]) > colsMax:
    #                     self.errorLog('Error. Well "' + well + '" number coordinate in location "' + location + '" is out of range')
    #                 else:
    #                     return letterIndex, int(well[1:])
    #         else:
    #             self.errorLog('Error. No well defined in location "' + location + '"')
    
class defaults:
    fileExtensions = {'ewt' : 'esc', 'gem' : 'gem'}
    washLine = {'ewt' : 'Wash(255,1,1,1,0,"2",500,"1.0",500,20,70,30,1,1,1000);', 'gem' : 'Wash(255,17,1,17,2,"2.0",500,"1.0",500,10,70,30,0,0,1000);'}

if __name__ == '__main__':
    prpr = Prpr_Tecan(310)
    print('Robot Config:')
    for element in prpr.robotConfig:
        print(element)