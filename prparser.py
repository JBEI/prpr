#!/usr/bin/env python3

# prparser.py, a part of PR-PR (previously known as PaR-PaR), a biology-friendly language for liquid-handling robots
# Author: Nina Stawski, nstawski@lbl.gov, me@ninastawski.com
# Copyright 2012-2013, Lawrence Berkeley National Laboratory
# http://github.com/JBEI/prpr/blob/master/license.txt

__author__ = 'Nina Stawski'
__version__ = '1.1'

import sys
import os
import argparse
import sqlite3
from prpr import *
from shutil import copyfile
from prpr_commands import *
from itertools import cycle
from copy import deepcopy
# from prpr_tecan import *
# from prpr_mf import *

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
        # self.tableSize = 31

    def addName(self, name):
        self.name = name
        self.log('Experiment name: ' + str(self.name))

    def addDocString(self, line):
        self.docString.append(line)

    def add(self, target, itemName, itemInfo):
        """
        usage: add(target, name, info)
        target: component|plate|volume|recipe|protocol|group
        """
        self.log('Added a ' + target + ' "' + itemName + '"')
        if target == 'component':
            platform = __import__('prpr_'+ self.platform)
            location = platform.PRPR.parseLocation(self, itemInfo.location) #self.parseLocation
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
            coords = wellInfo[1]#.split(',')
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

    def addMethods(self, userMethods, methods):
        if userMethods:
            if userMethods[0]:
                self.methods = userMethods + methods
            else:
                self.methods = methods + userMethods[1:]
        else:
            self.methods = methods

    def checkMethod(self, method):
        if self.platform == 'tecan' or  self.platform == 'human':
            if method in self.methods:
                return method
            else:
                if method != '' and method != 'Error' and method != 'None' and method != 'empty':
                    self.errorLog('Error. No such method on file: "' + str(method) + '"')
                    return 'Error'
                else:
                    return self.methods[0]
        elif self.platform == 'microfluidics':
            print('method for microfluidics', method)
            if isNumber(method):
                print('method for microfluidics is number', method)
                return method
            else:
                print('method for microfluidics is not number', method)
                return '100'
                #self.errorLog('Error in method "' + str(method) + '". Microfluidic methods should be numbers.')



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
            self.errorLog('Error. No ' + target + ' "' + itemName + '" defined. Please correct the error and try again.')

    def prepareLocation(self, component):
        location = []
        for comp in component:
            if len(comp) == 2:
                times = int(comp[1][1])
                if comp[1][0] == '|':
                    for well in comp[0].location:
                        for i in range(0, times):
                            location.append(well)
                if comp[1][0] == '*':
                    for i in range(0, times):
                        for well in comp[0].location:
                            location.append(well)
            else:
                for well in comp[0].location:
                    location.append(well)
        return location

    def createTransfer(self, source, destination, volume, transferMethod, line, wellsOnly = False):
        
        print('create transfer -->>', source, destination)
        #if component in self.components or ':' in component or self.platform == "microfluidics":
        #            if component in self.groups: #better parse groups
        #    if component in self.components:
        #        comp = self.components[component]
        #    elif component in self.mfWellLocations:
        #        comp = Component({'name': component, 'location': component, 'method': transferMethod})
        #        self.add('component', component, comp)
        #    else:
        #        if ':' in component:
        #            comp = Component({'name': component, 'location': component, 'method': self.methods[0]})
        #            self.add('component', component, comp)
        #        elif self.platform == 'microfluidics':
        #            comp = Component({'name': component, 'location': component, 'method': transferMethod})
        #            self.add('component', component, comp)
        
        method = ''
        methodError = False
        if transferMethod == 'DEFAULT':
            if self.platform == 'tecan' or self.platform == 'human':
                method = self.methods[0]
            elif self.platform == 'microfluidics':
                method = 100
        else:
            m = self.checkMethod(transferMethod)
            if m:
                method = m
            else:
                if self.platform == 'microscope':
                    method = transferMethod
                else:
                    methodError = True
                    self.log('Wrong method "' + transferMethod + '"')
                    self.errorLog('Error. Wrong method "' + transferMethod + '" in line "' + line + '"')
        if method:
            if volume in self.volumes:
                amount = self.volumes[volume].amount
            else:
                amount = volume
    
            if self.platform == 'tecan':
                volumeInfo = [self.splitAmount(x) for x in amount.split(',')]
            else:
                volumeInfo = amount
            if wellsOnly:
                src = source
                dst = destination
            else:
                src = self.prepareLocation(source)
                dst = self.prepareLocation(destination)
            transferDict = {'src': src, 'dst': dst, 'volume': volumeInfo, 'method': method, 'type': 'transfer'}
            print('transfer DICTIONARY', transferDict)
            return transferDict
        
        else:
            if not methodError:
                self.errorLog('Error. No method defined in line "' + line + '"')
                
        
        #else:
        #    self.log('Error. Wrong component "' + component + '".')
        #    self.errorLog('Error. Component "' + component + '" is not defined. Please correct the error and try again.')
        #    return False

### todo: separate by '/', ',' and '*' before calling platform location parse, common for all platforms, then parse location for both source and destination
        
        
    def parseGivenLocation(self, location, method=''):
        
        print('location in GIVEN Locations_________===', location)
        
        def CheckMultiplier(componentInfo):
            """
            Checks for additional actions on components
            """
            if self.platform == 'microscope':
                return [componentInfo]
            else:
                pipe = componentInfo.split('|')
                times = componentInfo.split('*')
                if len(pipe) == 2:
                    pipe[1] = ('|', pipe[1])
                    return pipe
                elif len(times) == 2:
                    times[1] = ('*', times[1])
                    return times
                else:
                    return [componentInfo]
            
        def CheckIfPlatePreDefined(locationInfo):
            plateAndWells = locationInfo.split(':')
            if len(plateAndWells) >1:
                if plateAndWells[0] in self.plates:
                    print('plateAndWell is in selfplates:::::::::::::::::', self.plates[plateAndWells[0]])
                    print('plateAndWell is in selfplates:::::::::::::::::', self.plates)
        
        splitLocations = []
        print('location in parseGivenLocation', location)
        
        locationPerPlate = location.split('/')
        print('locationPerPlate', locationPerPlate)
        
        tempLocations = []
        for plateLocation in locationPerPlate:
            singleLocations = plateLocation.split(',')
            print('singleLocation', singleLocations)
            for l in singleLocations:
                location = CheckMultiplier(l)
                
                if location[0] in self.components:
                    print('location is in self.components:', location)
                    print('here is location:', location)
                    prevLocations = ','.join(tempLocations)
                    location[0] = self.components[location[0]]
                    print('location now is:', location)
                    splitLocations.append(location)
                    if prevLocations != '':
                        lc = CheckMultiplier(prevLocations)
                        if self.platform == 'tecan':
                            method = self.methods[0]
                            
                        CheckIfPlatePreDefined(lc[0])
                        tempComponent = Component({'name': lc[0], 'location': lc[0], 'method': method})
                        print('location after check multiplier, no components: ', lc)
                        self.add('component', tempComponent.name, tempComponent)
                        lc[0] = self.components[location[0]]
                        print('location after check multiplier, added component: ', lc)
                        self.locations.append(lc)
                    tempLocations = []
                else:
                    print('location is NOT in self.components', l)
                    
                    tempLocations.append(l)
                    
            prevLocations = ','.join(tempLocations)
            if prevLocations != '':
                location = CheckMultiplier(prevLocations)
                if self.platform == 'tecan':
                    method = self.methods[0]
                    
                CheckIfPlatePreDefined(location[0])
                tempComponent = Component({'name': location[0], 'location': location[0], 'method': method})
                print('location after check multiplier, no components: ', location)
                self.add('component', tempComponent.name, tempComponent)
                location[0] = self.components[location[0]]
                print('location after check multiplier, added component: ', location)
                splitLocations.append(location)     
        
        print('splitlocations', splitLocations)
        return splitLocations
        
    def make(self, splitLine):
        originalLine = ' '.join(splitLine)
        line = splitLine[1:]
        if len(line) >= 3:
            if self.platform != 'human':
                self.addComment('------ BEGIN MAKE ' + line[0] + ' in ' + line[1] + ' ------')
            self.testindex += 1
            recipeInfo = line[0].split(':')

            if recipeInfo[0] in self.recipes:
                subrecipeError = False
                recipeName = self.recipes[recipeInfo[0]]
                recipe = []
                destination = self.parseGivenLocation(line[1])
                dstLocation = self.prepareLocation(destination)

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
                        for i, element in enumerate(a):
                            transferString = []
                            dst = dstLocation[i-1]
                            for z in element:
                                source = self.parseGivenLocation(z[0])
                                src = self.prepareLocation(source)[0]
                                volume = z[1]
                                transferMethod = line[2]
                                transaction = self.createTransfer(src, dst, volume, transferMethod, originalLine, wellsOnly=True)
                                if transaction:
                                    if self.platform != "microfluidics":
                                        transaction['volume'] = transaction['volume'][0]
                                    transferString.append(transaction)
                            if transferString:
                                self.transactionList.append(transferString)
                            #transferString = []
                            #z = zip(element, dstLocation)
                            #print('z!!', z)
                            #for i, el in enumerate(z):
                            #    print('el!!', el)
                            #    source = self.parseGivenLocation(el[0][0])
                            #    source[0][0].location = source[0][0].location[:1]
                            #    print('es******', source[0][0].location)
                            #    if self.platform != "microfluidics":
                            #        volume = el[0][1]
                            #    else:
                            #        volume = el[0]
                            #    print('source before :', source)
                            #    print('destination before :', destination)
                            #    #destination = el[1]
                            #    dst = deepcopy(destination)
                            #    dst[0][0].location = [dst[0][0].location[i]]
                            #    transferMethod = line[2]
                            #    modifier = ()
                            #    transaction = self.createTransfer(source, dst, volume, transferMethod, originalLine)
                            #    if transaction:
                            #        #transaction['src'] = transaction['src'][0] #making sure the transaction happens from one well (first if component has multiple wells)
                            #        if self.platform != "microfluidics":
                            #            transaction['volume'] = transaction['volume'][0]
                            #        transferString.append(transaction)
                            #if transferString:
                            #    self.transactionList.append(transferString)
                            #    for el in self.transactionList:
                            #        print('this is transaction list..........................', el)
                    else:
                        self.log('Error. Please specify the correct amount of wells in line: "' + originalLine + '".')
                        self.errorLog('Error. Please specify the correct amount of wells in line: "' + originalLine + '".')
                    if len(line) > 3:
                        options = line[3].split(',')
                        for option in options:
                            a = option.lower()
                            if a.startswith('mix'):
                                mixoptions = a.split(':')
                                if len(mixoptions) == 2:
                                    transaction = {'type': 'command', 'action': 'mix', 'options': mixoptions[1], 'location': self.prepareLocation(destination)}
                                    self.transactionList.append([transaction])
                                else:
                                    self.log('Error. Wrong mixing options in line "' + originalLine + '"')
                                    self.errorLog('Error. Wrong mixing options in line "' + originalLine + '". Please correct the error and try again.')
                else:
                    pass
            else:
                self.errorLog('Error. No such recipe as "' + recipeInfo[0] + '".')
            if self.platform != 'human':
                self.addComment('------ END MAKE ' + line[0] + ' in ' + line[1] + ' ------')
        else:
            self.errorLog('Error. Not enough parameters in line "' + originalLine + '". Please correct your script.')


    def transfer(self, splitLine, type):
        originalLine = ' '.join(splitLine)
        transferInfo = splitLine[1:]
        method = ''
        source = self.parseGivenLocation(transferInfo[0], method)
        destination = self.parseGivenLocation(transferInfo[1], method)
        
        if len(transferInfo) >= 4:
            if self.platform != 'human':
                self.addComment('------ BEGIN ' + type.upper() + ' ' + transferInfo[0] + ' to ' + transferInfo[1] + ' ------')
            self.testindex += 1
            
            volume = transferInfo[2]
            method = transferInfo[3]
            if self.platform == 'microfluidics':
                #method = transferInfo[3]
                if not isNumber(method):
                    if method == 'DEFAULT':
                        method = 100
                    elif method in self.volumes:
                        method = self.volumes[method].amount
                    else:
                        self.errorLog('Error in method "' + str(method) + '". Not found in defined methods.')
            transferLine = self.createTransfer(source, destination, volume, method, originalLine)
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
                        if self.platform == "tecan":
                            if len(vol) == 1:
                                trLine['volume'] = vol[0]
                            else:
                                try:
                                    trLine['volume'] = vol[i]  #volume is the problem!!!
                                except IndexError:
                                    self.errorLog('Error in line "' + originalLine + '". The number of volumes in "' + volume + '" is less than number of source wells.')
                        transfer.append(trLine)
                    self.transactionList.append(transfer)

                    if len(transferInfo) > 4:
                        options = transferInfo[4].split(',')
                        for option in options:
                            a = option.lower()
                            if a.startswith('mix'):
                                mixoptions = a.split(':')
                                if len(mixoptions) == 2:
                                    print('destination!!!', destination, self.prepareLocation(destination))
                                    transaction = {'type': 'command', 'action': 'mix', 'options': mixoptions[1], 'location': self.prepareLocation(destination)}
                                    self.transactionList.append([transaction])
                                else:
                                    self.log('Error. Wrong mixing options in line "' + originalLine + '"')
                    if self.platform != 'human':
                        self.addComment('------ END ' + type.upper() + ' ' + transferInfo[0] + ' to ' + transferInfo[1] + ' ------')

                else:
                    self.errorLog('Error in line "' + originalLine + '"')
        else:
            self.errorLog('Error. Not enough parameters in line "' + originalLine + '". Please correct your script.')

    def move(self, line, commandName):  #todo: add support for TRANSFER and COMPONENT commands
        if self.platform == 'microscope':
            self.testindex += 1
            self.addComment('------ BEGIN MOVE' + ' at location ' + line[0] + ' ' + line[2] + ' times with increments ' + line[1] + ' ------')
            transaction = []
            coords = line[0].split(',')
            increment = line[1].split(',')
            times = line[2]
            action = line[3]
            from ast import literal_eval
            coord_x = int(coords[0])
            coord_y = int(coords[1])
            coord_z = int(coords[2])
            transaction.append({'type': 'command', 'action': 'move', 'options': action, 'location': (coord_x, coord_y, coord_z)})
            for m in range(int(times)):
                coord_x = literal_eval(str(coord_x) + increment[0])
                coord_y = literal_eval(str(coord_y) + increment[1])
                coord_z = literal_eval(str(coord_z) + increment[2])
                transaction.append({'type': 'command', 'action': 'move', 'options': action, 'location': (coord_x, coord_y, coord_z)})
            self.transactionList.append(transaction)
            self.addComment('------ END MOVE' + ' at location ' + line[0] + ' ' + line[2] + ' times with increments ' + line[1] + ' ------')

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
            experiment.addComment('------ BEGIN PROTOCOL ' + self.name + ', variables: ' + ' '.join(self.variables) + '; values: ' + ' '.join(values) + ' ------')
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
        
        print('experiment wells in main', experiment.wells)
        
        list = [experiment.name,
                experiment.docString,

                experiment.wells,
                
                experiment.components,
                experiment.plates,
                experiment.volumes,
                experiment.recipes,

                experiment.transactionList,

                experiment.mfWellLocations,
                experiment.mfWellConnections]
        expID = str(experiment.ID)
        for element in list:
            if element:
                if element == experiment.name:
                    self.insert('ExperimentInfo', [experiment.ID, '"' + element + '"', '"' + '\n'.join(experiment.docString) + '"'])

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
                            
                            self.insert('Components', [expID, componentID, wellID])
                        self.insert('ComponentMethods', [expID, componentID, method])
                        self.insert('ComponentNames', [expID, componentID, name])

                elif element == experiment.wells:
                    for well in experiment.wells:
                    
                        wellID = str(id(well))
                        plate = '"' + str(well.plate) + '"'
                        location = '"' + str(well.location) + '"'
                        
                        print('well______ in wells:', expID, wellID, plate, location)
                        self.insert('Wells', [expID, wellID, plate, location])

                elif element == experiment.plates:
                    for plate in experiment.plates:
                        p = experiment.plates[plate]
                        grid = p.location[0]
                        site = p.location[1]
                        factoryName = '"' + p.factoryName + '"'
                        name = '"' + p.name + '"'
                        
                        plateLocationDescription = '"' + p.plateLocationDescription + '"'
                        
                        if plate != p.name:
                            nickname = '"' + plate + '"'
                            self.insert('PlateNicknames', [expID, name, nickname])
                        else:
                            self.insert('PlateLocations', [expID, name, factoryName, grid, site, plateLocationDescription])

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
                                self.insert('Transfers', [expID, actionID, trOrder, srcWellID, dstWellID, volume, method])

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
                                elif tr['action'] == 'move':
                                    location = '"' + str(tr['location']) + '"'
                                    self.insert('CommandLocations', [expID, actionID, str(t), location])

                elif element == experiment.mfWellLocations:
                    for key in element:
                        name = '"' + key + '"'
                        coords = '"' + element[key] + '"'
                        self.insert('mfWellLocations', [expID, name, coords])

                elif element == experiment.mfWellConnections:
                    for key in element:
                        well = '"' + key + '"'
                        for item in element[key]:
                            connection = '"' + item + '"'
                            self.insert('mfWellConnections', [expID, well, connection])

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
        list_ = DBHandler.db(message)
        for row in list_:
            methods.append(row[0])
        self.conn.commit()
        return methods
    
    def getPlates(self):
        plates = []
        message = 'SELECT * FROM Plates'
        plate_list = DBHandler.db(message)
        for row in plate_list:
            plates.append(row)
        self.conn.commit()
        return plates

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
    if stringCounter < 69:
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
                                    experiment.plates[plateNames[i]] = Plate(plateNames[i], tempPlates[i],(stringCounter, i), experiment.platform)
                                    experiment.log('Added a plate "' + tempPlates[i] + '" codename "' + plateNames[i] + '" at location ' + str((stringCounter, i + 1)))
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
                experiment.recipes[recipeName].addSubrecipe(lineName, {'name': lineName, 'line': lineNo, 'recipe': recipeLine})
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
                print('table is added', line[1], experiment.platform)
                if not experiment.tableAdded:
                    experiment.tableAdded = True
                    if __name__ == "__main__":
                        fileName = 'default_tables' + os.sep + line[1]
                    else:
                        fileName = line[1]
                    plateFile = open(fileName, "r")
                    experiment.log('Table file location: "' + fileName + '"')
                    if experiment.platform == 'microfluidics':
                        import prpr_microfluidics as platform
                        mfPlateFileParse(plateFile, experiment)
                    else:
                        import prpr_tecan as platform
                        fileExtension = fileName[-3:]
                        # copyfile(fileName, 'esc' + os.sep + 'config' + experiment.ID + '.esc')
                        copyfile(fileName, 'esc' + os.sep + 'config' + experiment.ID + '.' + platform.defaults.fileExtensions[fileExtension])
                        # copyfile(fileName, 'esc' + os.sep + 'config' + experiment.ID + '.gem')
                        PlateFileParse(plateFile, experiment, plateNicknames={}, plateIndexes={})

            elif command['name'] == 'volume':
                if len(line) == 3:
                #if line[2].isdigit():
                    volumeInfo = {'name': line[1], 'amount': line[2]}
                    experiment.add(command['name'], volumeInfo['name'], Volume(volumeInfo))
                #else:
                #   experiment.errorLog('Error. Volume value should be a digit in line "' + ' '.join(line) + '"')
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
                if len(line) >= 3:
                    plateNickname = line[1]
                    plateName = line[2]
                    plateLocationDescription = ''
                    if len(line) > 3:
                        plateLocationDescription = ' '.join(line[3:])

                    plateCoords = []
                    if plateName.find('*') != -1:
                        plateCoords = plateName.split('*')
                    elif plateName.find('x') != -1:
                        plateCoords = plateName.split('x')
                    if len(plateCoords) == 2:
                        row = plateCoords[0]
                        col = plateCoords[1]

                        plateInfo = Plate(plateNickname, plateNickname, plateCoords, experiment.platform, plateLocationDescription=plateLocationDescription, dimensions=(int(row), int(col)))
                        experiment.add('plate', plateNickname, plateInfo)
                    else:
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
            
            elif command['name'] == 'move':
                experiment.move(line[1:], command['name'])

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
    parser = argparse.ArgumentParser(description='Transfer liquids') #create the new argument parser for the command line arguments
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
    locationLine = mfTables[0]
    connections = mfTables[1:]
    experiment.addMFWellLocations(locationLine)
    experiment.addMFWellConnections(connections)

def isNumber(number):
    try:
        float(number)
        return True
    except ValueError:
        return False

if __name__ == '__main__':
    global experiment
    experiment = Experiment(maxVolume=150, tips=8, db=DBHandler(), platform="tecan")
    print('Experiment ID: ', experiment.ID)
    platform = __import__('prpr_'+ experiment.platform)
    ParseConfigFile(experiment)

    if not len(experiment.errorLogger):
        prpr = platform.PRPR(experiment.ID)
        print('Robot Config:')
        for element in prpr.robotConfig:
            print(element)
        print('Done. Check config.')

    else:
        print('Experiment terminated with errors.')
        for line in experiment.errorLogger:
            print(line)