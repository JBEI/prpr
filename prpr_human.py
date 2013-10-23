#!/usr/bin/env python3

# prpr_human.py, a part of PR-PR (previously known as PaR-PaR), a biology-friendly language for liquid-handling robots
# Author: Nina Stawski, nstawski@lbl.gov, me@ninastawski.com
# Copyright 2012-2013, Lawrence Berkeley National Laboratory
# http://github.com/JBEI/prpr/blob/master/license.txt

__author__ = 'Nina Stawski'
__version__ = '1.1'

import os
from prpr import *

class PRPR:
    wash = 'Wash or change the tips.'
    dictionary = {
        'en' : {
            'transfer' : 'transfer',
            'of' : 'of',
            'from' : 'from',
            'well' : 'well',
            'tube' : 'tube',
            'to' : 'to',
            'mix' : 'mix',
            'in' : 'in'
        },
        'ru' : {
            'transfer' : 'перенести',
            'of' : '',
            'from' : 'из',
            'well' : 'лунка',
            'tube' : 'пробирка',
            'to' : 'в',
            'mix' : 'перемешать',
            'in' : 'в'
        }
    }
    defaultMethodDescriptions = {
        'LC_W_Bot_Bot' : {
            'short': 'bottom to bottom',
            'long': 'Aspirate from bottom of the source well, dispense to the bottom of the destination well.'
        },
        'LC_W_Bot_Air' : {
            'short': 'bottom to air',
            'long': 'Aspirate from bottom of the source well, dispense from above the liquid level to the destination well.'
        },
        'LC_W_Bot_Lev' : {
            'short': 'bottom to level',
            'long': 'Aspirate from bottom of the source well, dispense at the liquid level of the destination well.'
        },
        'LC_W_Lev_Bot' : {
            'short': 'level to bottom',
            'long': 'Aspirate from the liquid level of the source well, dispense to the bottom of the destination well.'
        },
        'LC_W_Lev_Air' : {
            'short': 'level to air',
            'long': 'Aspirate from the liquid level of the source well, dispense from above the liquid level to the destination well.'
        },
        'LC_W_Lev_Lev' : {
            'short': 'level to level',
            'long': 'Aspirate from the liquid level of the source well, dispense at the liquid level of the destination well.'
        }
    }
    
    def __init__(self, ID):
        self.expID = ID
        self.usedMethods = []
        db = DatabaseHandler(ID)
        self.language = db.language
        self.transfers = db.transfers
        self.logger = []
        self.robotConfig = []
        self.transactions = []
        self.volumesList = []
        self.createTransfer()
        #self.addWash()
        self.addMethodDescriptions()
        self.saveLog()
        self.saveConfig()
        
    def addMethodDescriptions(self):
        info = ['Transfer method descriptions:', '']
        for method in self.usedMethods:
            info.append(self.defaultMethodDescriptions[method]['short'].capitalize() + ': ' + self.defaultMethodDescriptions[method]['long'])
            info.append('')
        self.robotConfig = info + self.robotConfig

    def createTransfer(self):
        allTransfers = self.transfers
        print('allTransfers', allTransfers)
        for transfer in allTransfers:
            print('transffffferrrr', transfer)
            trType = transfer['type']
            els = transfer['info']
            if trType == 'transfer':
                self.constructTransaction(els)

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
            fileName = file_
        with open(fileName, 'a', encoding='utf8') as myfile:
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
        
    def getLetterForWell(self, wellInfo):
        well = eval(wellInfo)
        alphabet = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'
        wellLetter = alphabet[well[0]-1]
        wellString = wellLetter + str(well[1])
        return wellString
        
    def getNumberForTube(self, wellInfo):
        well = eval(wellInfo)
        return str(well[1])

    def constructTransaction(self, transferList):
        """
        Creating the aspirate / dispense strings from the list of transfers
        """
        
        for tr in transferList:
            print('tr________________________', tr)
            volume = tr['volume']
            method = tr['method']
            if method not in self.usedMethods:
                self.usedMethods.append(method)
                
            if tr['source']['plateName'] == 'Tubes':
                sourceLocation = ' (' + self.dictionary[self.language]['tube'] + ' ' + self.getNumberForTube(tr['source']['well']) + ') '
            else:
                sourceLocation = ' (' + tr['source']['plateName'] + ' ' + self.dictionary[self.language]['well'] + ' ' + self.getLetterForWell(tr['source']['well']) + ') '
            if tr['destination']['plateName'] == 'Tubes':
                destinationLocation = ' (' + self.dictionary[self.language]['tube'] + ' ' + self.getNumberForTube(tr['destination']['well']) + ')'
            else:
                destinationLocation = ' (' + tr['destination']['plateName'] + ' ' + self.dictionary[self.language]['well'] + ' ' + self.getLetterForWell(tr['destination']['well']) + ')'
            
            transfer = self.dictionary[self.language]['transfer'].capitalize() + ' ' + volume + ' uL ' + self.dictionary[self.language]['of'] + ' "' + tr['source']['componentName'] + '" ' + self.dictionary[self.language]['from'] + sourceLocation + self.dictionary[self.language]['to'] + destinationLocation + ': ' + self.defaultMethodDescriptions[method]['short']
            self.config(transfer)

    def parseCommand(self, transferList):
        print('***************+___________', transferList)
        tr = transferList
        trList = []
        for option in tr:
            print('565656565-----------------', option)
            if option['command'] == 'mix':
                wellInfo = option['target']
                
                if wellInfo['plateName'] == 'Tubes':
                    mixLocation = ' (' + self.dictionary[self.language]['tube'] + ' ' + self.getNumberForTube(wellInfo['well']) + ') '
                else:
                    mixLocation = ' (' + wellInfo['plateName'] + ' ' + self.dictionary[self.language]['well'] + ' ' + self.getLetterForWell(wellInfo['well']) + ') '
                
                mix = self.dictionary[self.language]['mix'].capitalize() + ' "' + wellInfo['componentName'] + '" ' + self.dictionary[self.language]['in'] + mixLocation
                self.config(mix)
            elif (option['command'] == 'message') or (option['command'] == 'comment'):
                if option['message']:
                    if option['message'] != '$':
                        if len(self.robotConfig) and self.robotConfig[-1] != '':
                            self.config('')
                        self.config('# ' + option['message'])
                        if len(self.robotConfig) and self.robotConfig[-1] != '':
                            self.config('')
                    else:
                        self.config('')
        self.transactions.append(trList)
    
    def parseLocation(self, location):
        """
        Parses the given location, i.e. PL3:A1+4 to individual wells
        """

        def ParseWells(wells, plateDimensions):
            wellsLargeList = wells.split(',')
            wellsNewlist = []
            for well in wellsLargeList:
                wellsList = well.split('+')
                direction = 'vertical'
                if '-' in well:
                    wellsList = well.split('-')
                    direction = 'horizontal'
                elif '~' in well:
                    tempWellsList = well.split('~')
                    startWellCoords = GetWellCoordinates(tempWellsList[0], plateDimensions, str(location))
                    endWellCoords = GetWellCoordinates(tempWellsList[1], plateDimensions, str(location))
                    wellsAmount = (endWellCoords[0] - startWellCoords[0]) * plateDimensions[0] + endWellCoords[1] - startWellCoords[1] + 1
                    wellsList = (tempWellsList[0], wellsAmount)
                    direction = 'vertical'
                if wellsList[0]:
                    startWell = wellsList[0]
                    rowsMax = plateDimensions[0]
                    colsMax = plateDimensions[1]
                    if len(wellsList) == 2:
                        assert (wellsList[1] != ''), "Well number after '+' can't be empty."
                        numberWells = int(wellsList[1])
                        startCoords = GetWellCoordinates(startWell, plateDimensions, str(location))
                        for i in range(0, numberWells):
                            addedWells = WellsRename(startCoords, i, plateDimensions, direction)
                            assert(addedWells[1] <= colsMax), 'Wells locations are out of range'
                            wellsNewlist.append(addedWells)
                    elif len(wellsList) == 1:
                        wellsNewlist.append(GetWellCoordinates(wellsList[0], plateDimensions, str(location)))
                    else:
                        self.errorLog('Error. Can\'t be more than one \'+\'. Correct syntax in ' + str(location) + ' and run again. \n')
                else:
                    self.errorLog('Error. Well can\'t be empty in locaton "' + str(location) + '"')

            return wellsNewlist

        def WellsRename(startCoords, i, plateDimensions, direction):
            rowsMax = plateDimensions[0]
            colsMax = plateDimensions[1]
            currentNum = startCoords[0] + i
            if direction == 'vertical':
                if currentNum <= rowsMax:
                    newCol = startCoords[1]
                    return currentNum, newCol
                elif currentNum > rowsMax:
                    times = int(currentNum / rowsMax)
                    newCol = startCoords[1] + times
                    newRow = currentNum - (times * rowsMax)
                    if newRow == 0:
                        return newRow + rowsMax, newCol - 1
                    else:
                        return newRow, newCol
            if direction == 'horizontal':
                if currentNum <= colsMax:
                    newRow = startCoords[1]
                    return newRow, currentNum
                elif currentNum > colsMax:
                    times = int(currentNum / colsMax)
                    newRow = startCoords[1] + times
                    newCol = currentNum - (times * colsMax)
                    if newCol == 0:
                        return newRow - 1, newCol + colsMax
                    else:
                        return newRow, newCol


        def GetWellCoordinates(well, plateDimensions, location):
            """
            Takes the well coordinates entered by the user and dimensions of the plate and returns the wells plate coordinates
            """
            if well:
                rowsMax = plateDimensions[0]
                colsMax = plateDimensions[1]
                try:
                    int(well)
                    well = int(well)
                    if well > rowsMax * colsMax:
                        self.errorLog('Error. Well "' + str(well) + '" in location "' + location + '" is out of range')
                    else:
                        if well <= rowsMax:
                            newCol = 1
                            newRow = well
                        else:
                            times = int(well / rowsMax)
                            newCol = times + 1
                            newRow = well - (times * rowsMax)
                        if newRow == 0:
                            return newRow + rowsMax, newCol - 1
                        else:
                            return newRow, newCol
                except ValueError:
                    alphabet = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'
                    letterIndex = alphabet.find(well[:1]) + 1
                    if letterIndex > rowsMax:
                        self.errorLog('Error. Well "' + well + '" letter coordinate in location "' + location + '" is out of range')
                    elif int(well[1:]) > colsMax:
                        self.errorLog('Error. Well "' + well + '" number coordinate in location "' + location + '" is out of range')
                    else:
                        return letterIndex, int(well[1:])
            else:
                self.errorLog('Error. No well defined in location "' + location + '"')
                
                
        loc = []
        if '/' in location:
            newLoc = location.split('/')
        else:
            newLoc = [location]
        for line in newLoc:
            if ':' in location:
                plateAndWells = line.split(':')
                if plateAndWells[0]:
                    if plateAndWells[0] in self.plates:
                        plateName = self.plates[plateAndWells[0]].name
                        plateDms = self.plates[plateAndWells[0]].dimensions
                        plateLocation = self.plates[plateAndWells[0]].location
    
                        if plateAndWells[1]:
                            wells = ParseWells(plateAndWells[1], plateDms)
                            for well in wells:
                                if (plateName, location) in filter(lambda x: (x.plate, x.location), self.wells):
                                    print('aiaiaiaiaiaiaiai!!!!')
                                w = Well({'Plate': plateName, 'Location': well}) #todo: append well only if there are no same wells registered; otherwise error
                                loc.append(w)
                                self.wells.append(w)
                                print('self wells in Tecan', self.wells)
                                #                    else:
                                #                        self.errorLog('Error. No wells in location "' + str(location) + '"')
                    else:
                        self.errorLog('Error. No such plate in the system "' + str(plateAndWells[0]) + '"')
                else:
                    self.errorLog('Error. No plate in location "' + str(location) + '"')
            else:
                plate = self.platform
                wellLocation = location
                w = Well({'Plate' : plate, 'Location' : wellLocation})
                self.wells.append(w)
                loc.append(w)
            
            
                           
        return loc

    
class defaults:
    fileExtensions = {'txt' : 'txt'}

if __name__ == '__main__':
    prpr = PRPR(310)
    print('Config:')
    for element in prpr.robotConfig:
        print(element)