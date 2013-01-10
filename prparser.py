#!/usr/bin/env python3
__author__ = 'Nina Stawski'
__version__ = '0.32'

import sys
import os
import argparse
import sqlite3
from prpr import *
from shutil import copyfile
from prpr_commands import *
from itertools import cycle
from copy import deepcopy

#todo: switch to postgres

class Experiment:
    def __init__(self, maxVolume, tips, db, platform, userMethods=''):
        """
        New experiment with parameters:
        robotTips - maximum amount of tips the robot has
        maxVolume - maximum capacity of a tip
        """
        self.name = ''
        self.platform = platform
        self.components = {}
        self.plates = {}
        self.volumes = {}
        self.recipes = {}
        self.tableAdded = False
        self.dosStringAdded = False
        self.docString = []
        self.transactionList = []
        self.logger = []
        self.wells = []
        self.testindex = 0
        self.ID = str(db.selectMax('Experiments'))
        self.robotTips = tips
        self.maxVolume = maxVolume
        db.insert('Experiments', [self.ID, self.robotTips, self.maxVolume, '"' + self.platform + '"'])
        self.log('Experiment ID: ' + str(self.ID))
        self.errorLogger = []
        self.protocols = {}
        self.addMethods(userMethods, db.getMethods())
        self.groups = {} #note: group{name:[component1, component2]}
        self.mfWellLocations = {}
        self.mfWellConnections = {}

    def addName(self, name):
        self.name = name
        self.log('Experiment name: ' + str(self.name))

    def addDocString(self, line):
        print('line', line)
        self.docString.append(line)

    def add(self, target, itemName, itemInfo):
        """
        usage: add(target, name, info)
        target: component|plate|volume|recipe|protocol|group
        """
        self.log('Added a ' + target + ' "' + itemName + '"')
        if target == 'component':
            location = self.parseLocation(itemInfo.location)
            method = self.checkMethod(itemInfo.method)
            if method:
                itemInfo.method = method
            if location:
                itemInfo.location = location
            self.components[itemName] = itemInfo
        elif target == 'plate':
            self.plates[itemName] = itemInfo
        elif target == 'volume':
            self.volumes[itemName] = itemInfo
        elif target == 'recipe':
            self.recipes[itemName] = itemInfo
        elif target == 'protocol':
            self.protocols[itemName] = itemInfo
        elif target == 'group':
            self.groups[itemName] = itemInfo

    def addMFWellLocations(self, wellLocationString):
        locations = wellLocationString.split(';')[:-1]
        for location in locations:
            wellInfo = location.split(':')
            well = wellInfo[0]
            coords = wellInfo[1].split(',')
            self.mfWellLocations[well] = coords

    def addMFWellConnections(self, wellConnectionString):
        for welInfo in wellConnectionString:
            wellConnections = welInfo.strip().split(':')
            well = wellConnections[0]
            connections = wellConnections[1].split(',')
            for connection in connections:
                if well in self.mfWellConnections:
                    self.mfWellConnections[well].append(connection)
                else:
                    self.mfWellConnections[well] = [connection]
                if connection in self.mfWellConnections:
                    self.mfWellConnections[connection].append(well)
                else:
                    self.mfWellConnections[connection] = [well]
        print(self.mfWellConnections)

    def addMethods(self, userMethods, methods):
        if userMethods:
            if userMethods[0]:
                self.methods = userMethods + methods
            else:
                self.methods = methods + userMethods[1:]
        else:
            self.methods = methods

    def checkMethod(self, method):
        if method in self.methods:
            return method
        else:
            if method != '' and method != 'Error' and method != 'None' and method != 'empty':
                self.errorLog('Error. No such method on file: "' + str(method) + '"')
                return 'Error'
            else:
                return self.methods[0]

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
                    wellsAmount = (endWellCoords[0] - startWellCoords[0]) * plateDimensions[0] + endWellCoords[1] -
                    startWellCoords[1] + 1
                print('(', endWellCoords[0], '-', startWellCoords[0], ') *', plateDimensions[0], '-',
                    endWellCoords[1], '+', startWellCoords[1])
                print(startWellCoords, endWellCoords, plateDimensions, wellsAmount)
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
                    self.errorLog('Error. Can\'t be more than one \'+\'. Correct syntax in ' + str(
                        location) + ' and run again. \n')
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
                    self.errorLog(
                        'Error. Well "' + well + '" letter coordinate in location "' + location + '" is out of range')
                elif int(well[1:]) > colsMax:
                    self.errorLog(
                        'Error. Well "' + well + '" number coordinate in location "' + location + '" is out of range')
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
                        w = Well({'Plate': plateName,
                                  'Location': well}) #todo: append well only if there are no same wells registered; otherwise error
                        loc.append(w)
                        self.wells.append(w)
                        #                    else:
                        #                        self.errorLog('Error. No wells in location "' + str(location) + '"')
            else:
                self.errorLog('Error. No such plate in the system "' + str(plateAndWells[0]) + '"')
        else:
            self.errorLog('Error. No plate in location "' + str(location) + '"')
    return loc


def splitAmount(self, volume):
    maxVolume = int(self.maxVolume)
    if volume.isdigit():
        splitAmount = volume.split('.')
        if len(splitAmount) > 1: # works for small volumes only
            amount = float(volume)
        else:
            amount = int(volume)
        if amount < maxVolume:
            return amount, 1
        else:
            times = amount / maxVolume
            left = amount - maxVolume * int(times)
            if left > 0:
                tipsNeeded = int(times)
                newAmount = (maxVolume, tipsNeeded, left)
            else:
                tipsNeeded = int(times)
                newAmount = (maxVolume, tipsNeeded)
            return newAmount
    else:
        self.errorLog('Error, volume "' + volume + '" is not defined. Please correct the error and try again.')


def get(self, target, itemName):
    if target == 'component':
        item = self.components
    elif target == 'plate':
        item = self.plates
    elif target == 'volume':
        item = self.volumes
    elif target == 'recipe':
        item = self.recipes
    else:
        item = False
    assert item, 'Wrong target name, "' + target + '"'
    if itemName in item.keys():
        return item[itemName]
    else:
        self.log('Error. No ' + target + ' "' + itemName + '" defined.')
        self.errorLog(
            'Error. No ' + target + ' "' + itemName + '" defined. Please correct the error and try again.')


def createTransfer(self, component, modifier, destination, volume, transferMethod, line):
    if component in self.components or ':' in component:
    #            if component in self.groups: #better parse groups
        if component in self.components:
            comp = self.components[component]
        else:
            if ':' in component:
                comp = Component({'name': component, 'location': component, 'method': self.methods[0]})
                self.add('component', component, comp)
        method = ''
        methodError = False
        if transferMethod == 'DEFAULT':
            method = self.methods[0]
        else:
            m = self.checkMethod(transferMethod)
            if m:
                method = m
            else:
                methodError = True
                self.log('Wrong method "' + transferMethod + '"')
                self.errorLog('Error. Wrong method "' + transferMethod + '" in line "' + line + '"')
        if method:
            location = []
            if modifier:
                times = int(modifier[1])
                if modifier[0] == '|':
                    for well in comp.location:
                        for i in range(0, times):
                            location.append(well)
                if modifier[0] == '*':
                    for i in range(0, times):
                        for well in comp.location:
                            location.append(well)
            else:
                location = comp.location

            if volume in self.volumes:
                amount = self.volumes[volume].amount
            else:
                amount = volume

            volumeInfo = [self.splitAmount(x) for x in amount.split(',')]

            transferDict = {'src': location, 'dst': destination, 'volume': volumeInfo, 'method': method,
                            'type': 'transfer'}
            return transferDict

        else:
            if not methodError:
                self.errorLog('Error. No method defined in line "' + line + '"')
    else:
        self.log('Error. Wrong component "' + component + '".')
        self.errorLog(
            'Error. Component "' + component + '" is not defined. Please correct the error and try again.')
        return False


def make(self, splitLine):
    originalLine = ' '.join(splitLine)
    line = splitLine[1:]
    if len(line) >= 3:
        self.addComment('------ BEGIN MAKE ' + line[0] + ' in ' + line[1] + ' ------')
        self.testindex += 1
        recipeInfo = line[0].split(':')

        if recipeInfo[0] in self.recipes:
            subrecipeError = False
            recipeName = self.recipes[recipeInfo[0]]
            recipe = []
            if line[1] not in self.components:
                if ':' in line[1]:
                    dest = Component({'name': line[1], 'location': line[1], 'method': self.methods[0]})
                    self.add('component', dest.name, dest)
                else:
                    self.errorLog(
                        'Error. Wrong component "' + line[1] + '". Please correct the error and try again.')
            else:
                dest = self.components[line[1]]
            dstLocation = dest.location

            if len(recipeInfo) == 2:
                subrecipes = recipeInfo[1].split(',')
                for sub in subrecipes:
                    if sub in recipeName.subrecipes:
                        recipe.append(recipeName.subrecipes[sub]['recipe'])
                    else:
                        subrecipeError = True
                        self.errorLog('Error. No such line "' + str(sub) + '" in recipe "' + recipeInfo[0] + '"')
            else:
                recipeLines = sorted(recipeName.subrecipes.values(), key=lambda k: k['line'])
                for rLine in recipeLines:
                    recipe.append(rLine['recipe'])
            if not subrecipeError:
                if len(recipe) == len(dstLocation):
                    a = zip(*recipe)
                    for element in a:
                        transferString = []
                        z = zip(element, dstLocation)
                        for el in z:
                            component = el[0][0]
                            volume = el[0][1]
                            destination = el[1]
                            transferMethod = line[2]
                            modifier = ()
                            transaction = self.createTransfer(component, modifier, destination, volume,
                                transferMethod, originalLine)
                            if transaction:
                                transaction['src'] = transaction['src'][
                                                     0] #making sure the transaction happens from one well (first if component has multiple wells)
                                transaction['volume'] = transaction['volume'][0]
                                transferString.append(transaction)
                        if transferString:
                            self.transactionList.append(transferString)
                else:
                    self.log('Error. Please specify the correct amount of wells in line: "' + originalLine + '".')
                    self.errorLog(
                        'Error. Please specify the correct amount of wells in line: "' + originalLine + '".')

                if len(line) > 3:
                    options = line[3].split(',')
                    for option in options:
                        a = option.lower()
                        if a.startswith('mix'):
                            mixoptions = a.split(':')
                            if len(mixoptions) == 2:
                                transaction = {'type': 'command', 'action': 'mix', 'options': mixoptions[1],
                                               'location': dest.location}
                                self.transactionList.append([transaction])
                            else:
                                self.log('Error. Wrong mixing options in line "' + originalLine + '"')
                                self.errorLog(
                                    'Error. Wrong mixing options in line "' + originalLine + '". Please correct the error and try again.')
            else:
                pass
        else:
            self.errorLog('Error. No such recipe as "' + recipeInfo[0] + '".')

        self.addComment('------ END MAKE ' + line[0] + ' in ' + line[1] + ' ------')
    else:
        self.errorLog('Error. Not enough parameters in line "' + originalLine + '". Please correct your script.')


def transfer(self, splitLine, type):
    originalLine = ' '.join(splitLine)
    transferInfo = splitLine[1:]

    def CheckMultiplier(componentInfo):
        """
        Checks for additional actions on components
        """
        pipe = componentInfo.split('|')
        times = componentInfo.split('*')
        pipe.insert(0, '|')
        times.insert(0, '*')
        if len(pipe) > 2:
            return pipe
        elif len(times) > 2:
            return times
        else:
            return componentInfo

    if len(transferInfo) >= 4:
        self.addComment(
            '------ BEGIN ' + type.upper() + ' ' + transferInfo[0] + ' to ' + transferInfo[1] + ' ------')
        self.testindex += 1

        #check the source for multipliers
        check = CheckMultiplier(transferInfo[0])
        modifier = ()
        if len(check) == 3:
            modifier = (check[0], check[2])
            source = check[1]
        else:
            source = check
        if transferInfo[1] not in self.components:
            dest = Component({'name': transferInfo[1], 'location': transferInfo[1], 'method': self.methods[0]})
            self.add('component', dest.name, dest)
            dst = self.components[dest.name]

        else:
            dst = self.components[transferInfo[1]]
        destination = dst.location
        volume = transferInfo[2]
        method = transferInfo[3]
        transferLine = self.createTransfer(source, modifier, destination, volume, method, originalLine)
        if transferLine:
            newTr = False

            if type == 'transfer':
                if len(transferLine['src']) == len(transferLine['dst']):
                    newTr = enumerate(zip(transferLine['src'], transferLine['dst']))

            elif type == 'spread':
                newTr = enumerate(zip(cycle(transferLine['src']), transferLine['dst']))

            transfer = []
            if newTr:
                vol = transferLine['volume']
                for i, tr in newTr:
                    trLine = deepcopy(transferLine)
                    trLine['src'] = tr[0]
                    trLine['dst'] = tr[1]
                    if len(vol) == 1:
                        trLine['volume'] = vol[0]
                    else:
                        try:
                            trLine['volume'] = vol[i]
                        except IndexError:
                            self.errorLog(
                                'Error in line "' + originalLine + '". The number of volumes in "' + volume + '" is less than number of source wells.')
                    transfer.append(trLine)
                self.transactionList.append(transfer)

                if len(transferInfo) > 4:
                    options = transferInfo[4].split(',')
                    for option in options:
                        a = option.lower()
                        if a.startswith('mix'):
                            mixoptions = a.split(':')
                            if len(mixoptions) == 2:
                                transaction = {'type': 'command', 'action': 'mix', 'options': mixoptions[1],
                                               'location': dst.location}
                                self.transactionList.append([transaction])
                            else:
                                self.log('Error. Wrong mixing options in line "' + originalLine + '"')
                self.addComment(
                    '------ END ' + type.upper() + ' ' + transferInfo[0] + ' to ' + transferInfo[1] + ' ------')

            else:
                self.errorLog('Error in line "' + originalLine + '"')
    else:
        self.errorLog('Error. Not enough parameters in line "' + originalLine + '". Please correct your script.')


def message(self, line):
    message = {'type': 'command', 'action': 'message', 'options': line}
    self.transactionList.append([message])


def addComment(self, line):
    comment = {'type': 'command', 'action': 'comment', 'options': line}
    self.transactionList.append([comment])


def log(self, item):
    from datetime import datetime

    time = str(datetime.now())
    print(item)
    self.logger.append(time + ': ' + item)


def errorLog(self, item):
    self.errorLogger.append(item)


class Well:
    def __init__(self, dict):
        self.plate = dict['Plate']
        self.location = dict['Location']


class Component:
#    method = 'LC_W_Bot_Bot'
    def __init__(self, dict):
        self.name = dict['name']
        self.location = dict['location']
        self.shortLocation = dict['location']
        if 'method' in dict:
            self.method = dict['method']
        else:
            self.method = 'empty'


class Plate:
    def __init__(self, plateName, factoryName, plateLocation):
        self.name = plateName
        self.factoryName = factoryName
        self.location = plateLocation
        db = DBHandler.db('SELECT Rows, Columns from Plates WHERE FactoryName=' + '"' + factoryName + '"')
        self.dimensions = db[0]


class Volume:
    def __init__(self, dict):
        self.name = dict['name']
        self.amount = dict['amount']


class Recipe:
    def __init__(self, name):
        self.subrecipes = {}
        self.name = name
        self.lineCounter = 0

    def addSubrecipe(self, name, info):
        self.subrecipes[name] = info


class Protocol:
    def __init__(self, protocolInfo):
        self.name = protocolInfo['name']
        self.variables = protocolInfo['variables']
        self.info = []

    def addInfo(self, info):
        self.info.append(info)

    def addValues(self, values, experiment):
        if len(self.variables) == len(values):
            readyProtocol = self.info
            newProtocol = []
            for i in range(0, len(readyProtocol)):
                mystring = readyProtocol[i]
                newProtocol.append(mystring)
                for v in range(0, len(values)):
                    newProtocol[i] = newProtocol[i].replace(self.variables[v], values[v])
            from tempfile import TemporaryFile

            protocolFile = TemporaryFile(mode='r+')
            protocolFile.writelines(newProtocol)
            protocolFile.seek(0)
            line = protocolFile.readline()
            experiment.addComment('------ BEGIN PROTOCOL ' + self.name + ', variables: ' + ' '.join(
                self.variables) + '; values: ' + ' '.join(values) + ' ------')
            while line != '':
                splitline = line.split()
                LineToList(splitline, protocolFile, experiment)
                line = protocolFile.readline()
            experiment.addComment('------ END PROTOCOL ' + self.name + ' ------')


class DBHandler:
    def __init__(self):
        self.conn = sqlite3.connect('prpr.db')
        self.crsr = self.conn.cursor()

    def createExperiment(self, experiment):
        self.experiment = experiment

        expID = experiment.ID
        maxTips = experiment.robotTips
        maxVolume = experiment.maxVolume
        platform = experiment.platform

        self.insert('Experiments', [expID, maxTips, maxVolume, '"' + platform + '"'])

    def insert(self, destination, items):
        list = []
        for item in items:
            list.append(str(item))
        values = ', '.join(list)
        message = 'INSERT INTO ' + destination + ' Values(' + values + ');'
        try:
            self.crsr.execute(message)
        except sqlite3.IntegrityError:
            pass
        self.conn.commit()

    def update(self, destination, items, filter=''):
        message = 'UPDATE ' + destination + ' SET ' + items + ' WHERE ExpID = ' + self.experiment.ID
        if filter != '':
            message += ' AND ' + filter
        self.crsr.execute(message)
        self.conn.commit()

    def selectMax(self, destination, expID=''):
        destinations = {
            'Experiments': 'ExpID',
            'Components': 'ComponentID',
            'Wells': 'WellID',
            'Transfers': 'TransferID'
        }
        if destination in destinations:
            message = 'SELECT Max(' + destinations[destination] + ') FROM ' + destination
            if destination != 'Experiments':
                message += ' WHERE ExpID=' + expID
            self.crsr.execute(message)
            id = self.crsr.fetchone()
            if id is None:
                return 1
            else:
                return id[0] + 1

    def updateExperiment(self, experiment):
        """
        Dumps experiment information into database
        """
        self.experiment = experiment
        list = [experiment.name,
                experiment.docString,

                experiment.components,
                experiment.plates,
                experiment.volumes,
                experiment.recipes,

                experiment.transactionList]
        expID = str(experiment.ID)
        for element in list:
            if element:
                if element == experiment.name:
                    self.insert('ExperimentInfo',
                        [experiment.ID, '"' + element + '"', '"' + '\n'.join(experiment.docString) + '"'])

                elif element == experiment.components:
                    for component in experiment.components:
                        c = experiment.components[component]
                        componentID = str(id(c))
                        method = '"' + c.method + '"'
                        name = '"' + c.name + '"'
                        for well in c.location:
                            wellID = str(id(well))
                            plate = '"' + str(well.plate) + '"'
                            location = '"' + str(well.location) + '"'
                            self.insert('Wells', [expID, wellID, plate, location])
                            self.insert('Components', [expID, componentID, wellID])
                        self.insert('ComponentMethods', [expID, componentID, method])
                        self.insert('ComponentNames', [expID, componentID, name])

                elif element == experiment.plates:
                    for plate in experiment.plates:
                        p = experiment.plates[plate]
                        grid = p.location[0]
                        site = p.location[1]
                        factoryName = '"' + p.factoryName + '"'
                        name = '"' + p.name + '"'
                        if plate != p.name:
                            nickname = '"' + plate + '"'
                            self.insert('PlateNicknames', [expID, name, nickname])
                        else:
                            self.insert('PlateLocations', [expID, name, factoryName, grid, site])

                elif element == experiment.volumes:
                    for volume in experiment.volumes:
                        v = experiment.volumes[volume]
                        volumeName = '"' + v.name + '"'
                        volumeValue = '"' + v.amount + '"'
                        self.insert('Volumes', [expID, volumeName, volumeValue])

                elif element == experiment.recipes:
                    for recipe in experiment.recipes:
                        r = experiment.recipes[recipe]
                        recipe = '"' + r.name + '"'
                        for subrecipe in r.subrecipes:
                            s = r.subrecipes[subrecipe]
                            row = str(s['line'])
                            name = '"' + s['name'] + '"'
                            self.insert('Subrecipes', [expID, recipe, row, name])
                            for element in s['recipe']:
                                column = str(s['recipe'].index(element))
                                rName = '"' + element[0] + '"'
                                rVolume = '"' + element[1] + '"'
                                self.insert('Recipes', [expID, recipe, row, column, rName, rVolume])

                elif element == experiment.transactionList:
                    for i in range(0, len(experiment.transactionList)):
                        actionID = str(i)
                        transaction = experiment.transactionList[i]
                        trType = '"' + transaction[0]['type'] + '"'
                        self.insert('Actions', [expID, actionID, trType])
                        for t in range(0, len(transaction)):
                            tr = transaction[t]
                            trOrder = str(t)
                            if tr['type'] == 'transfer':
                                srcWellID = str(id(tr['src']))
                                dstWellID = str(id(tr['dst']))
                                volume = '"' + str(tr['volume']) + '"'
                                method = '"' + str(tr['method']) + '"'
                                self.insert('Transfers',
                                    [expID, actionID, trOrder, srcWellID, dstWellID, volume, method])

                            if tr['type'] == 'command':
                                command = '"' + tr['action'] + '"'
                                options = '"' + tr['options'] + '"'
                                self.insert('Commands', [expID, actionID, trOrder, command, options])
                                if tr['action'] == 'mix':
                                    locationList = tr['location']
                                    m = t
                                    for l in locationList:
                                        self.insert('CommandLocations', [expID, actionID, str(m), str(id(l))])
                                        m += 1

    def close(self):
        self.conn.commit()
        self.crsr.close()
        self.conn.close()

    def getMethods(self):
        methods = []
        message = 'SELECT Method FROM DefaultMethod'
        default = DBHandler.db(message)[0][0]
        methods.append(default)

        message = 'SELECT Method FROM Methods'
        list = DBHandler.db(message)
        for row in list:
            methods.append(row[0])
        self.conn.commit()
        return methods

    @staticmethod
    def checkIfMethodExists(method):
        """
        Checks if the method entered by the user exists in the database.
        """
        methods = []
        list = DBHandler.db('select * from Methods')
        for row in list:
            methods.append(row[0])
        if method in methods: return method

    @staticmethod
    def db(request):
        conn = sqlite3.connect('prpr.db')
        c = conn.cursor()
        c.execute(request)
        q = c.fetchall()
        conn.commit()
        c.close()
        conn.close()
        return q


def ParseLocation(locationLine):
    """
    ParseLocation gets a string and splits it a few times.
    As a result, it returns a list of dictionaries that contain plate/well locations for a certain reagent.
    """
    locationStore = []
    for item in locationLine.split('/'):
        locationDict = {}
        location = item.split(':')
        locationDict['Plate'] = location[0]
        locationDict['Wells'] = location[1]
        locationStore.append(locationDict)
    return locationStore


def PlateFileParse(plateFile, experiment, plateNicknames, plateIndexes):
    """
    Gets plate names and locations from the table file
    """
    plateLine = plateFile.readline()
    global stringCounter
    stringCounter = 0
    while plateLine != '':
        parts = plateLine.strip().split(';')
        PlateNameParse(parts, plateFile, experiment, plateNicknames, plateIndexes)
        plateLine = plateFile.readline()


def PlateNameParse(parts, plateFile, experiment, plateNicknames, plateIndexes):
    global stringCounter
    if stringCounter < 31:
        if parts[0] == '998':
            if len(parts) >= 2:
                n_plates = parts[1]
                if n_plates.isdigit():
                    if n_plates != '0':
                        plates = parts[2:int(n_plates) + 2]
                        counter = len(plates)
                        tempPlates = []
                        for plate in plates:
                            tempPlates.append(plate)
                        plateLine = plateFile.readline()
                        plateNames = plateLine.strip().split(';')[1:-1]
                        for i in range(counter):
                            if (plateNames[i] != '') and (tempPlates[i] != ''):
                                plateNicknames[plateNames[i]] = tempPlates[i]
                                plateIndexes[plateNames[i]] = (stringCounter, i)
                                if experiment:
                                    experiment.plates[plateNames[i]] = Plate(plateNames[i], tempPlates[i],
                                        (stringCounter, i))
                                    experiment.log('Added a plate "' + tempPlates[i] + '" codename "' + plateNames[
                                                                                                        i] + '" at location ' + str(
                                        (stringCounter, i + 1)))
                stringCounter += 1
                return plateNicknames


def SaveToFile(information, filename):
    """
    Writes something to a file. Saves a log.
    """
    writefile = open(filename, "w")
    writefile.writelines("%s\n" % item for item in information)
    print('Experiment log saved as ' + filename)


def ParseRecipe(configFileName, recipeName, experiment):
    """
    Goes through the recipe line-by-line and adds it to the list until the end of the recipe found.
    """
    unsplitline = configFileName.readline()
    line = unsplitline.split()
    if line:
        if not CheckCommand(line[0]):
            if unsplitline[0] != '#':
                lineName = line[0][0:-1]
                uncutLine = line[1:]
                experiment.recipes[recipeName].lineCounter += 1
                lineNo = experiment.recipes[recipeName].lineCounter
                recipeLine = []
                for reagent, volume in zip(uncutLine[::2], uncutLine[1::2]):
                    recipeLine.append((reagent, volume))
                experiment.recipes[recipeName].addSubrecipe(lineName,
                    {'name': lineName, 'line': lineNo, 'recipe': recipeLine})
            ParseRecipe(configFileName, recipeName, experiment)
        else:
            LineToList(line, configFileName, experiment)


def ParseProtocol(configFileName, protocolName, experiment):
    line = configFileName.readline()
    command = ''
    protocol = experiment.protocols[protocolName]
    if line.strip():
        test = CheckCommand(line.split()[0])
        if test:
            command = test['name']
    if command != 'endprotocol':
        protocol.addInfo(line)
        ParseProtocol(configFileName, protocolName, experiment)
    else:
        LineToList(line.split(), configFileName, experiment)


def ParseDocstring(fileName, experiment):
    line = fileName.readline().split()
    if line:
        c = CheckCommand(line[0])
        if c:
            if c['name'] == '"""':
                return
            else:
                experiment.addDocString(' '.join(line))
                ParseDocstring(fileName, experiment)
        else:
            experiment.addDocString(' '.join(line))
            ParseDocstring(fileName, experiment)
    else:
        experiment.addDocString(' '.join(line))
        ParseDocstring(fileName, experiment)


def LineToList(line, configFileName, experiment):
    if line:
        command = CheckCommand(line[0])
        if command:
            if command['name'] == 'name':
                experiment.addName(' '.join(line[1:]))

            elif command['name'] == 'component':
                componentInfo = {'name': line[1], 'location': line[2]}
                if len(line) > 3:
                    componentInfo['method'] = experiment.checkMethod(line[3])
                experiment.add(command['name'], componentInfo['name'], Component(componentInfo))

            elif command['name'] == 'table':
                if not experiment.tableAdded:
                    experiment.tableAdded = True
                    if __name__ == "__main__":
                        fileName = 'default_tables' + os.sep + line[1]
                    else:
                        fileName = line[1]
                    plateFile = open(fileName, "r")
                    experiment.log('Table file location: "' + fileName + '"')
                    if experiment.platform == 'microfluidics':
                        mfPlateFileParse(plateFile, experiment)
                    else:
                        copyfile(fileName, 'esc' + os.sep + 'config' + experiment.ID + '.esc')
                        PlateFileParse(plateFile, experiment, plateNicknames={}, plateIndexes={})

            elif command['name'] == 'volume':
                if len(line) == 3:
                #                    if line[2].isdigit():
                    volumeInfo = {'name': line[1], 'amount': line[2]}
                    experiment.add(command['name'], volumeInfo['name'], Volume(volumeInfo))
                #                    else:
                #                        experiment.errorLog('Error. Volume value should be a digit in line "' + ' '.join(line) + '"')
                else:
                    experiment.errorLog('Error. Please correct the volume info in line "' + ' '.join(line) + '"')

            elif command['name'] == 'recipe':
                recipe = Recipe(line[1])
                experiment.add(command['name'], recipe.name, recipe)
                ParseRecipe(configFileName, recipe.name, experiment)

            elif command['name'] == '"""':
                if not experiment.dosStringAdded:
                    ParseDocstring(configFileName, experiment)
                    experiment.dosStringAdded = True
                else:
                    experiment.log('Docstring already added for this experiment.')

            elif command['name'] == 'plate':
                if len(line) == 3:
                    plateNickname = line[1]
                    plateName = line[2]
                    experiment.plates[plateNickname] = experiment.plates[plateName]
                    experiment.log('Added a nickname "' + plateNickname + '" to the plate name "' + plateName + '"')
                else:
                    experiment.errorLog('Error. Wrong parameter count in line "' + ' '.join(line) + '"')

            elif command['name'] == 'protocol':
                protocolInfo = {'name': line[1], 'variables': line[2:]}
                protocol = Protocol(protocolInfo)
                experiment.add(command['name'], protocol.name, protocol)
                ParseProtocol(configFileName, protocol.name, experiment)

            elif command['name'] == 'use':
                protocolName = line[1]
                values = line[2:]
                experiment.protocols[protocolName].addValues(values, experiment)

            elif command['name'] == 'make':
                experiment.make(line)

            elif command['name'] == 'transfer' or command['name'] == 'spread':
                experiment.transfer(line, command['name'])

            elif command['name'] == 'message':
                experiment.message(' '.join(line[1:]))

            elif command['name'] == 'comment':
                experiment.addComment(' '.join(line[1:]))

        elif line[0].startswith('#'):
            return

        else:
            experiment.log('Error, no such command: "' + line[0] + '"')
            experiment.errorLog('Error, no such command: "' + line[0] + '". Please correct the error and try again.')


def ParseConfigFile(experiment):
    parser = argparse.ArgumentParser(
        description='Transfer liquids') #create the new argument parser for the command line arguments
    parser.add_argument('config_file_name', type=argparse.FileType('r'), default=sys.stdin, help='Config file')
    args = parser.parse_args()
    ParseFile(args.config_file_name, experiment)


def ParseFile(filename, experiment):
    """
    ParseFile reads the file string by string
    Usage:
    filename - full path to the file in relation to current folder
    experiment - an object of a class Experiment()
    """
    global expName
    global setList
    setList = []
    line = filename.readline()
    while line != '':
        oneline = line.split()
        LineToList(oneline, filename, experiment)
        line = filename.readline()
    logname = 'logs/experiment' + experiment.ID + '.log'
    SaveToFile(experiment.logger, logname)
    db = DBHandler()
    db.updateExperiment(experiment)


def mfPlateFileParse(plateFile, experiment):
    mfTables = plateFile.readlines()
    print('mfTables', mfTables)
    locationLine = mfTables[0]
    connections = mfTables[1:]
    print('mfPlateFileParse', locationLine, connections)
    experiment.addMFWellLocations(locationLine)
    experiment.addMFWellConnections(connections)


if __name__ == '__main__':
    global experiment
    experiment = Experiment(maxVolume=150, tips=8, db=DBHandler(), platform="freedomevo")
    print('Experiment ID: ', experiment.ID)
    ParseConfigFile(experiment)

    if not len(experiment.errorLogger):
        prpr = Prpr(experiment.ID)
        print('Robot Config:')
        for element in prpr.robotConfig:
            print(element)
        print('Done. Check config.')

    else:
        print('Experiment terminated with errors.')
        for line in experiment.errorLogger:
            print(line)