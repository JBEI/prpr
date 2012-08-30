#!/usr/bin/env python3.2
__author__ = 'Nina Stawski'
__version__ = '0.3'

import sys
import os
import argparse
import sqlite3
from parpar import *
from shutil import copyfile
from parpar_commands import *
from itertools import cycle
from copy import deepcopy

#todo: switch to postgres

class Experiment:
    name = ''
    components = {}
    plates = {}
    volumes = {}
    recipes = {}
    robotTips = 8
    maxVolume = 150
    tableAdded = False
    dosStringAdded = False
    docString = []
    transactionList = []
    logger = []
    wells = []
    testindex = 0

    def __init__(self, maxVolume, tips, db):
        self.ID = str(db.selectMax('Experiments'))
        self.robotTips = tips
        self.maxVolume = maxVolume
        db.insert('Experiments', [self.ID, self.robotTips, self.maxVolume])
        self.log('Experiment ID: ' + str(self.ID))

    def addName(self, name):
        self.name = name
        self.log('Experiment name: ' + str(self.name))

    def addDocString(self, filename):
        line = filename.readline().split()
        if line:
            self.docString.append(' '.join(line))
            c = CheckCommand(line[0])
            if c:
                if c['name'] == '"""':
                    return
            else:
                self.addDocString(filename)

        else:
            self.addDocString(filename)

    def add(self, target, itemName, itemInfo):
        """
        usage: addItem(target, name, info)
        target: component|plate|volume|recipe
        """
        self.log('Added a ' + target + ' "' + itemName + '"')
        if target == 'component':
            itemInfo.location = self.parseLocation(itemInfo.location)
            self.components[itemName] = itemInfo
        elif target == 'plate':
            self.plates[itemName] = itemInfo
        elif target == 'volume':
            self.volumes[itemName] = itemInfo
        elif target == 'recipe':
            self.recipes[itemName] = itemInfo

    def parseLocation(self, location):

        def ParseWells(wells, plateDimensions):
            wellsLargeList = wells.split(',')
            wellsNewlist = []
            for well in wellsLargeList:
                wellsList = well.split('+')
                direction = 'vertical'
                if '-' in well:
                    wellsList = well.split('-')
                    direction = 'horizontal'
                startWell = wellsList[0]
                rowsMax = plateDimensions[0]
                colsMax = plateDimensions[1]
                if len(wellsList) == 2:
                    assert (wellsList[1] != ''), "Well number after '+' can't be empty."
                    numberWells = int(wellsList[1])
                    startCoords = GetWellCoordinates(startWell, plateDimensions)
                    for i in range(0, numberWells):
                        addedWells = WellsRename(startCoords, i, plateDimensions, direction)
                        assert(addedWells[1] <= colsMax), 'Wells locations are out of range'
                        wellsNewlist.append(addedWells)
                elif len(wellsList) == 1:
                    wellsNewlist.append(GetWellCoordinates(wellsList[0], plateDimensions))
                else:
                    self.log('Can\'t be more than one \'+\'. Correct syntax in ' + str(location) + ' and run again. \n')
            return wellsNewlist

        def WellsRename(startCoords, i, plateDimensions, direction):
            rowsMax = plateDimensions[0]
            colsMax = plateDimensions[1]
#            print('12', rowsMax, colsMax, plateDimensions, i)
            currentNum = startCoords[0] + i
            if direction == 'vertical':
                if currentNum <= rowsMax:
                    newCol = startCoords[1]
                    return currentNum, newCol
                elif currentNum > rowsMax:
                    times = int(currentNum/rowsMax)
                    newCol = startCoords[1] + times
                    newRow = currentNum - (times * rowsMax)
                    if newRow == 0:
                        return newRow + rowsMax, newCol -1
                    else:
                        return newRow, newCol
            if direction == 'horizontal':
                if currentNum <= colsMax:
                    newRow = startCoords[1]
                    return newRow, currentNum
                elif currentNum > colsMax:
                    times = int(currentNum/colsMax)
                    newRow = startCoords[1] + times
                    newCol = currentNum - (times * colsMax)
                    if newCol == 0:
                        return newRow -1, newCol + colsMax
                    else:
                        return newRow, newCol


        def GetWellCoordinates(well, plateDimensions):
            """
            Takes the well coordinates entered by the user and dimensions of the plate and returns the wells plate coordinates
            """
            rowsMax = plateDimensions[0]
            colsMax = plateDimensions[1]
            try:
                int(well)
                well = int(well)
                assert (well <= rowsMax*colsMax), 'Well number is out of range'
                if well <= rowsMax:
                    newCol = 1
                    newRow = well
                else:
                    times = int(well/rowsMax)
                    newCol = times + 1
                    newRow = well - (times * rowsMax)
                if newRow == 0:
                    return newRow + rowsMax, newCol - 1
                else:
                    return newRow, newCol
            except ValueError:
                alphabet = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'
                letterIndex = alphabet.find(well[:1]) + 1
                assert (letterIndex <= rowsMax), 'Well letter coordinate is out of range'
                assert (int(well[1:]) <= colsMax), 'Well number coordinate is out of range'
                return letterIndex, int(well[1:])
        loc = []
        if '/' in location:
            newLoc = location.split('/')
        else:
            newLoc = [location]
        for line in newLoc:
            plateAndWells = line.split(':')
            plateName = self.plates[plateAndWells[0]].name
            plateDms = self.plates[plateAndWells[0]].dimensions
            plateLocation = self.plates[plateAndWells[0]].location
            wells =  ParseWells(plateAndWells[1], plateDms)
            for well in wells:
                if (plateName, location) in filter(lambda x: (x.plate, x.location), self.wells):
                    print('aiaiaiaiaiaiaiai!!!!')
                w = Well({'Plate' : plateName, 'Location' : well})
                loc.append(w)
                self.wells.append(w)
        return loc

    def splitAmount(self, volume):
        maxVolume = int(self.maxVolume)
        if volume in self.volumes:
            amount = self.volumes[volume].amount
        else:
            amount = volume
        splitAmount = amount.split('.')
        if len(splitAmount) > 1: # works for small volumes only
            amount = float(amount)
        else:
            amount = int(amount)
        if amount < maxVolume:
            return (amount, 1)
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
        assert item , 'Wrong target name, "' + target + '"'
        if itemName in item.keys():
            return item[itemName]
        else:
            self.log('Error. No ' + target + ' "' + itemName + '" defined.')

    def createTransfer(self, component, destination, volume, transferMethod):
        if component in self.components:
            comp = self.components[component]
        else:
            if ':' in component:
                comp = Component({'name' : component, 'location' : component})
                self.add('component', component, comp)
        if transferMethod == 'DEFAULT':
            method = comp.method
        else:
            m = DatabaseHandler.checkIfMethodExists(transferMethod)
            if m:
                method = m
            else:
                self.log('Wrong method "' + transferMethod + '"')

        return {'src' : comp.location, 'dst' : destination, 'volume' : self.splitAmount(volume), 'method' : method, 'type' : 'transfer'}

    def checkIfComponentExists(self, component):
        for c in self.components:
            if component in self.components[c].shortLocation:

                print('your component in short location ', component)

    def make(self, line):
        self.testindex += 1
        recipeInfo = line[0].split(':')
        recipeName = self.recipes[recipeInfo[0]]
        recipe = []
        if line[1] not in self.components:
            dest = Component({'name' : line[1], 'location' : line[1]})
            self.add('component', dest.name, dest)
        else:
            dest = self.components[line[1]]
        dstLocation = dest.location

        if len(recipeInfo) == 2:
            subrecipes = recipeInfo[1].split(',')
            for sub in subrecipes:
                recipe.append(recipeName.subrecipes[sub]['recipe'])
        else:
            recipeLines = sorted(recipeName.subrecipes.values(), key=lambda k: k['line'])
            for rLine in recipeLines:
                recipe.append(rLine['recipe'])
        if len(recipe) == len(dstLocation):
            a = zip(*recipe)
            for element in a:
                transferString = []
                z = zip(element, dstLocation)
                for el in z:
                    component = el[0][0]
#                    self.checkIfComponentExists(component)
                    volume = el[0][1]
                    destination = el[1]
                    transferMethod = line[2]
                    transaction = self.createTransfer(component, destination, volume, transferMethod)
                    transaction['src'] = transaction['src'][0] #making sure the transaction happens from one well (first if component has multiple wells)
                    transferString.append(transaction)
                self.transactionList.append(transferString)
        else:
            self.log('Error. Please specify the correct amount of wells in line: "MAKE  ' + '  '.join(line) + '".')


        if len(line) > 3:
            options = line[3].split(',')
            for option in options:
                a = option.lower()
                if a.startswith('mix'):
                    mixoptions = a.split(':')
                    if len(mixoptions) == 2:
                        transaction = {'type' : 'command', 'action' : 'mix', 'options' : mixoptions[1], 'location' : dest.location}
                        self.transactionList.append([transaction])
                    else:
                        self.log('Error. Wrong mixing options in "' + line + '"')

    def transfer(self, transferInfo, type):
        self.testindex += 1
        source = transferInfo[0]
        if transferInfo[1] not in self.components:
            dest = Component({'name' : transferInfo[1], 'location' : transferInfo[1]})
            self.add('component', dest.name, dest)
        else:
            dest = self.components[transferInfo[1]]
        destination = dest.location
        volume = transferInfo[2]
        method = transferInfo[3]

        transferLine = self.createTransfer(source, destination, volume, method)

        if type == 'transfer':
            if len(transferLine['src']) == len(transferLine['dst']):
                newTr = zip(transferLine['src'], transferLine['dst'])

        if type == 'spread':
            newTr = zip(cycle(transferLine['src']), transferLine['dst'])

        transfer = []
        for tr in newTr:
            trLine = deepcopy(transferLine)
            trLine['src'] = tr[0]
            trLine['dst'] = tr[1]
            transfer.append(trLine)
        self.transactionList.append(transfer)

        if len(transferInfo) > 4:
            options = transferInfo[4].split(',')
            for option in options:
                a = option.lower()
                if a.startswith('mix'):
                    mixoptions = a.split(':')
                    if len(mixoptions) == 2:
                        transaction = {'type' : 'command', 'action' : 'mix', 'options' : mixoptions[1], 'location' : dest.location}
                        self.transactionList.append([transaction])
                    else:
                        self.log('Error. Wrong mixing options in "' + transferInfo + '"')
    def message(self, line):
        message = {'type' : 'command', 'action' : 'message', 'options' : line}
        self.transactionList.append([message])

    def log(self, item):
        from datetime import datetime
        time = str(datetime.now())
        print(item)
        self.logger.append(time + ': ' + item)

class Well:
    plate = ''
    location = ''
    def __init__(self, dict):
        self.plate = dict['Plate']
        self.location = dict['Location']

class Component:
    method = 'LC_W_Bot_Bot'
    def __init__(self, dict):
        self.name = dict['name']
        self.location = dict['location']
        self.shortLocation = dict['location']
        if 'method' in dict:
            self.method = dict['method']

class Plate:
    name = ''
    location = ''
    factoryName = ''
    dimensions = ''
    def __init__(self, plateName, factoryName, plateLocation):
        self.name = plateName
        self.factoryName = factoryName
        self.location = plateLocation
        db = DatabaseHandler.db('SELECT Rows, Columns from Plates WHERE FactoryName=' + '"' + factoryName + '"')
        self.dimensions = db[0]

class Volume:
    name = ''
    def __init__(self, dict):
        self.name = dict['name']
        self.amount = dict['amount']

class Recipe:
    name = ''
    subrecipes = {}

    def __init__(self, name):
        self.name = name
        self.lineCounter = 0

    def addSubrecipe(self, name, info):
        self.subrecipes[name] = info


class DatabaseHandler:
    def __init__(self):
        self.conn = sqlite3.connect('parpar.db')
        self.crsr = self.conn.cursor()

    def createExperiment(self, experiment):
        self.experiment = experiment

        expID = experiment.ID
        maxTips = experiment.robotTips
        maxVolume = experiment.maxVolume

        self.insert('Experiments', [expID, maxTips, maxVolume])

    def insert(self, destination, items):
        list = []
        for item in items:
            list.append(str(item))
        values = ', '.join(list)
        self.crsr.execute('INSERT INTO ' + destination + ' Values(' + values + ');')
        self.conn.commit()

    def update(self, destination, items, filter = ''):
        message = 'UPDATE ' + destination + ' SET ' + items + ' WHERE ExpID = ' + self.experiment.ID
        if filter != '':
            message += ' AND ' + filter
        self.crsr.execute(message)
        self.conn.commit()

    def selectMax(self, destination, expID=''):
        destinations = {
            'Experiments' : 'ExpID',
            'Components' : 'ComponentID',
            'Wells' : 'WellID',
            'Transfers' : 'TransferID'
        }
        if destination in destinations:
            message = 'SELECT Max(' + destinations[destination] + ') FROM ' + destination
            if destination != 'Experiments':
                message += ' WHERE ExpID=' + expID
            self.crsr.execute(message)
            id = self.crsr.fetchone()
            if id == None:
                return 1
            else:
                return id[0] + 1

    def updateExperiment(self, experiment):
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
                        volumeValue = v.amount
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
                                    for l in locationList:
                                        self.insert('CommandLocations', [expID, actionID, str(id(l))])

    def close(self):
        self.conn.commit()
        self.crsr.close()
        self.conn.close()

    @staticmethod
    def checkIfMethodExists(method):
        """
        Checks if the method entered by the user exists in the database.
        """
        methods = []
        list = DatabaseHandler.db('select * from Methods')
        for row in list:
            methods.append(row[0])
        if method in methods: return method

    @staticmethod
    def db(request):
        conn = sqlite3.connect('parpar.db')
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
    plateLine = plateFile.readline()
    global stringCounter
    stringCounter = 0
    while plateLine != '':
        parts = plateLine.strip().split(';')
        PlateNameParse(parts, plateFile, experiment, plateNicknames, plateIndexes)
        plateLine = plateFile.readline()

def PlateNameParse(parts, plateFile, experiment, plateNicknames, plateIndexes): #NEW parse plate names
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
                                    experiment.plates[plateNames[i]] = Plate(plateNames[i], tempPlates[i], (stringCounter, i))
                                    experiment.log('Added a plate "' + tempPlates[i] + '" codename "' + plateNames[i] + '" at location ' + str((stringCounter, i+1)))
                stringCounter += 1
                return plateNicknames

def SaveToFile(information, filename):
    """
    Writes something to a file. Saves a log.
    """
    writefile = open(filename, "w")
    writefile.writelines( "%s\n" % item for item in information )
    print('Experiment log saved as ' + filename)

def ParseRecipe(configFileName, recipeName, experiment):
    """
    Goes through the recipe line-by-line and adds it to the list until the 'ENDRECIPE' found.
    """
    unsplitline = configFileName.readline()
    line = unsplitline.split()
    if line:
        if unsplitline[0] != '#':
#            if ':' in line[0][-1]:
            lineName = line[0][0:-1]
            uncutLine = line[1:] #everything except the line name
            experiment.recipes[recipeName].lineCounter += 1
            lineNo = experiment.recipes[recipeName].lineCounter
#            else:
#                recipe.addSubrecipe(lineNo, {'line' : lineNo})
#                uncutLine = line
            recipeLine = []
            for reagent, volume in zip(uncutLine[::2], uncutLine[1::2]):
                recipeLine.append((reagent, volume))
            experiment.recipes[recipeName].addSubrecipe(lineName, {'name' : lineName, 'line' : lineNo, 'recipe' : recipeLine})
        ParseRecipe(configFileName, recipeName, experiment)
        
def ParseReagent(reagentLine, expID):
    """
    Gets a list made from the line containing reagent information, parses it to the reagent dictionary.
    """
    plateAndWell = ParseReagentInfo(reagentLine[1], expID)[0]
    if len(reagentLine) <3 or reagentLine[2] == 'DEFAULT':
        method = 'LC_W_Bot_Bot'
    else:
        method = reagentLine[2]
    reagentDict = {'Name' : reagentLine[0], 'Plate' : plateAndWell['Plate'], 'Wells' : plateAndWell['Wells'], 'Method' : method}
    #todo: parse the separate wells and call ParseWells() on every bit.
    return reagentDict

def ParseReagentInfo(reagentInfo, expID):
    """
    Get a string containing information about the reagent.
    Check either reagent name or well coordinates against the reagents already in the database (what do we do with this information?)
    If there is a name and reagent is in the database, get its coordinates
    Return parsed coordinates of the reagent
    """
    if ':' in reagentInfo:
        reagent = LocationFunction(reagentInfo, expID)
    else:
        #note: parse what will happen if there are two names used (for example: water,sugar)
        reagentRaw = []
        #todo: for each plate name, join wells together
        DatabaseConnect()
        crsr.execute('SELECT Plate, Location, Method FROM (ReagentNames NATURAL JOIN Reagents NATURAL JOIN Wells) WHERE Wells.ExpID = ' + expID + ' AND Name = ' + '"' + reagentInfo + '"')
        for row in crsr:
            reagentRaw.append({'Plate' : row[0], 'Wells' : row[1], 'Method' : row[2]})
        DatabaseDisconnect()
        reagent = []
        plateInfo = reagentRaw[0]['Plate']
        #todo: change the style to make it more visible on what gets updated and what's not
        for r in range(0, len(reagentRaw)):
            if reagentRaw[r]['Plate'] != plateInfo:
                reagent.append({'Plate' : plateInfo, 'Wells' : eval(reagentRaw[r]['Wells']), 'Method' : reagentRaw[r]['Method']})
            else:
                if len(reagent) == 0:
                    reagent.append({'Plate' : plateInfo, 'Wells' : [eval(reagentRaw[r]['Wells'])], 'Method' : reagentRaw[r]['Method']})
                else:
                    reagent[len(reagent) - 1]['Wells'].append(eval(reagentRaw[r]['Wells']))
    return reagent

    
def LineToList(line, configFileName, experiment):
    if line:
        command = CheckCommand(line[0])
        if command:

            if command['name'] == 'name':
                experiment.addName(' '.join(line[1:]))

            elif command['name'] == 'component':
                componentInfo = {'name' : line[1], 'location' : line[2]}
                if len(line) > 3:
                    componentInfo['method'] = line[3]
                experiment.add(command['name'], componentInfo['name'], Component(componentInfo))

            elif command['name'] == 'table':
                if not experiment.tableAdded:
                    experiment.tableAdded = True
                    tablefolder = 'tables' + os.sep
                    fileName = tablefolder + line[1]
                    copyfile(tablefolder + line[1], 'esc' + os.sep + 'config' + experiment.ID + '.esc')
                    plateFile = open(fileName, "r")
                    experiment.log('Table file location: "' + fileName + '"')
                    PlateFileParse(plateFile, experiment, plateNicknames={}, plateIndexes={})

            elif command['name'] == 'volume':
                volumeInfo = {'name': line[1], 'amount' : line[2]}
                experiment.add(command['name'], volumeInfo['name'], Volume(volumeInfo))

            elif command['name'] == 'recipe':
                recipe = Recipe(line[1])
                experiment.add(command['name'], recipe.name, recipe)
                ParseRecipe(configFileName, recipe.name, experiment)

            elif command['name'] == '"""':
                if not experiment.dosStringAdded:
                    experiment.dosStringAdded = True
                    experiment.addDocString(configFileName)
                else:
                    experiment.log('Docstring already added for this experiment.')

            elif command['name'] == 'plate':
                plateNickname = line[1]
                plateName = line[2]
                experiment.plates[plateNickname] = experiment.plates[plateName]
                experiment.log('Added a nickname "' + plateNickname + '" to the plate name "' + plateName + '"')

            elif command['name'] == 'make':
                experiment.make(line[1:])

            elif command['name'] == 'transfer' or command['name'] == 'spread':
                experiment.transfer(line[1:], command['name'])

            elif command['name'] == 'message':
                experiment.message(' '.join(line[1:]))


        elif line[0].startswith('#'):
#            experiment.log(' '.join(line))
            return

        else:
            experiment.log('Error, no such command: "' + line[0] + '"')

#
#        #note: loading information from file
#        elif line[0] == 'LOAD':
#            loadFile = open(line[1] + '.xls', "r")
#            reagentPlate = line[2]
#            reagentMethod = line[3]
#            loadLines = loadFile.readlines()
#            for r in range(1, len(loadLines)):
#                lineList = loadLines[r].split()
#                for c in range(1, len(lineList)):
#                    rDict = {'Name' : lineList[c], 'Plate' : reagentPlate, 'Wells' : [(r, c)], 'Method': reagentMethod}
#                    DatabaseConnect()
#                    AddElements('Reagents', rDict, expID)
#                    DatabaseDisconnect()


def ParseConfigFile(experiment):
    parser = argparse.ArgumentParser(description = 'Transfer liquids') #create the new argument parser for the command line arguments
    parser.add_argument('config_file_name', type = argparse.FileType('r'), default = sys.stdin, help = 'Config file')
    args = parser.parse_args()
    ParseFile(args.config_file_name, experiment)
#    if not args.log:
#        print('hey!')

def ParseFile(filename, experiment):
    """
    ParseFile reads the file string by string  ###     expID = experiment.ID
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
    SaveToFile(experiment.logger, logname) #save log
    db = DatabaseHandler()
    db.updateExperiment(experiment)

if __name__ == '__main__':
    global experiment
    experiment = Experiment(maxVolume=150,tips=8,db=DatabaseHandler())
    print('Experiment ID: ', experiment.ID)
    ParseConfigFile(experiment)

    parpar = ParPar(experiment.ID)
    print('Robot Config:')
    for element in parpar.robotConfig:
        print(element)
    print('Done. Check config.')
