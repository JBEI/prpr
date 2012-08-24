#!/usr/bin/env python3.2
__author__ = 'Nina Stawski'

import sys
import os
import argparse
import sqlite3
import parpar
from shutil import copyfile

global robotTips
global maxAm
robotTips = 8
maxAm = 150

#todo: switch to postgres

class Well:
    ID = ''
    Plate = ''
    Location = ''
    def __init__(self, plate, location):
        self.plate = GetPlate()

class Reagent: #todo: use classes and other structures to keep information in
    Name = ''
    Plate = ''
    Well = []
    Method = 'LC_W_Bot_Bot' #default method #todo: choose it if the config reads 'default'
    Volume = ''
    def __init__(self, defReagent):
        self.Name = defReagent[1] #assign name to the reagent
        self.Plate = defReagent[2] #assign reagent to the plate
        # self.Well = ParseWells(defReagent[3]) #assign reagent to the well(s)
        self.Well = defReagent[3]
        method = CheckIfMethodExists(defReagent[4])
        self.Method = method #assign the transfer method to the reagent #FIXME: make the default method work as well as assign
        # self.Volume = 
        
class Plate:
    Nickname = ''
    Name = ''
    Rows = ''
    Columns = ''
    Location = ''
    def __init__(self, name, rows, columns):
        self.Name = ''
        self.DefaultName = defPlate[2] #get the default plate name
        self.Location = defPlate[3] #assign the plate to location

def CheckIfMethodExists(method):
    """
    Checks if the method entered by the user exists in the database.
    """
    methods = []
    DatabaseConnect()
    crsr.execute('select * from Methods')
    for row in crsr:
        methods.append(row[0])
    assert (method in methods), 'Error, no such method in list'
    DatabaseDisconnect()
    return method
    
def ParseWells(wells, plateDimensions): #todo: include parsing of additional wells notation
    wellsLargeList = wells.split(',')
    wellsNewlist = []
    for well in wellsLargeList:
        print('wellslist', well)
        wellsList = well.split('+')
        startWell = wellsList[0]
        rowsMax = plateDimensions[0]
        colsMax = plateDimensions[1]
        if len(wellsList) == 2:
            assert (wellsList[1] != ''), "Well number after '+' can't be empty."
            numberWells = int(wellsList[1])
            startCoords = GetWellCoordinates(startWell, plateDimensions)
            for i in range(0, numberWells):
                addedWells = WellsRename(startCoords, i, plateDimensions)
                assert(addedWells[1] <= colsMax), 'Wells locations are out of range'
                wellsNewlist.append(addedWells)
        elif len(wellsList) == 1:
            wellsNewlist.append(GetWellCoordinates(wellsList[0], plateDimensions))
        else:
            sys.exit("Can't be more than one '+'. Correct syntax and run again. \n")
    return wellsNewlist

def WellsRename(startCoords, i, plateDimensions):
    rowsMax = plateDimensions[0]
    colsMax = plateDimensions[1]
    currentNum = startCoords[0] + i
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

def LocationFunction(locationLine, expID):
    """
    Get a string and parse it to a list of location dictionaries.
    """
    if '/' in locationLine:
        location = locationLine.split('/')
    else:
        location = [locationLine]
    for line in location:
        plateAndWells = line.split(':')
        platename = GetPlateName(plateAndWells[0], expID)
        plateDms = GetPlate(platename, expID)[1:]
        plateLocation = GetPlateLocation(platename, expID)
        wells = ParseWells(plateAndWells[1], plateDms)
        location[location.index(line)] = {'Plate' : platename, 'Wells' : wells, 'PlateDimensions' : plateDms, 'PlateLocation' : plateLocation}
    return location

def GetPlate(plateName, expID):
    """
    Gets the plate from the database based on given nickname or original name of the plate
    """
    DatabaseConnect()
    tryFirst = 'SELECT FactoryName, Rows, Columns from (Plates NATURAL JOIN PlateLocations NATURAL JOIN PlateNicknames) WHERE Nickname=' + '"' + plateName + '"' + ' AND ExpID = ' + expID
    crsr.execute(tryFirst)
    plate = crsr.fetchone()
    if plate == None:
        command = 'SELECT FactoryName, Rows, Columns from (Plates NATURAL JOIN PlateLocations) WHERE Plate=' + '"' + plateName + '"' + ' AND ExpID = ' + expID
        crsr.execute(command)
        plate = crsr.fetchone()
        return plate
    else:
        return plate
    
def GetPlateLocation(plateName, expID):
    DatabaseConnect()
    tryFirst = 'SELECT Grid, Site from (PlateLocations NATURAL JOIN PlateNicknames) WHERE Nickname=' + '"' + plateName + '"' + ' AND ExpID = ' + expID
    crsr.execute(tryFirst)
    plateLoc = crsr.fetchone()
    if plateLoc == None:
        command = 'SELECT Grid, Site from PlateLocations WHERE Plate=' + '"' + plateName + '"' + ' AND ExpID = ' + expID
        crsr.execute(command)
        plateLoc =  crsr.fetchone()
        return plateLoc
    else:
        return plateLoc

def GetPlateName(plateName, expID):
    DatabaseConnect()
    try:
        message = 'SELECT Plate from PlateLocations WHERE Plate=' + '"' + plateName + '"' + ' AND ExpID = ' + expID
        crsr.execute(message)
        plate = crsr.fetchone()[0]
    except TypeError:
        message = 'SELECT Plate from  (PlateLocations NATURAL JOIN PlateNicknames) WHERE Nickname=' + '"' + plateName + '"' + ' AND ExpID = ' + expID
        crsr.execute(message)
        plate = crsr.fetchone()[0]
    return plate

def PlateFileParse(plateFile, plateIndexes, plateNicknames):
    plateLine = plateFile.readline()
    global stringCounter
    stringCounter = 0
    while plateLine != '':
        parts = plateLine.strip().split(';')
        PlateNameParse(parts, plateNicknames, plateIndexes, plateFile)
        plateLine = plateFile.readline()
    print(plateIndexes, plateNicknames)

def PlateNameParse(parts, plateNicknames, plateIndexes, plateFile): #NEW parse plate names
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
                stringCounter += 1
                return plateNicknames

def SaveToFile(information, filename):
    """
    Writes something to a file. Needed just for debug purposes.
    """
    writefile = open(filename, "w")
    writefile.writelines( "%s\n" % item for item in information )

def ParseRecipe(configFileName, recipe):
    """
    Goes through the recipe line-by-line and adds it to the list until the 'ENDRECIPE' found.
    """
    unsplitline = configFileName.readline()
    line = unsplitline.split()
    #todo: add a cutline that cuts off the name of the line, and add this name of the line to the database
    if line:
        if unsplitline[0] != '#':
            recipeLine = []
            if ':' in line[0][-1]:
                lineName = line[0]
                uncutLine = line[1:]
                recipeLine.append(lineName[0:-1])
            else:
                uncutLine = line
            for reagent, volume in zip(uncutLine[::2], uncutLine[1::2]):
                recipeLine.append((reagent, volume))
            recipe.append(recipeLine)
        ParseRecipe(configFileName, recipe)
        
def GetReagentLocation(reagentName):
    message = 'SELECT Plate, Wells FROM ReagentLocations WHERE Name = ' + '"' + reagentName + '"' + ' AND ExpID = ' + expID
    DatabaseConnect()
    crsr.execute(message)
    rLocation = []
    for row in crsr:
        rLocation.append(row[0])
        rLocation.append(row[1])
    DatabaseDisconnect()
    return rLocation
        
def ParseDoc(configFileName, configDict):
    line = configFileName.readline().split()
    if line:
        if line[0] != '"""':
            configDict.append(' '.join(line))
            ParseDoc(configFileName, configDict)
    else:
        ParseDoc(configFileName, configDict)
        
def ParseReagent(reagentLine, expID):
    """
    Gets a list made from the line containing reagent information, parses it to the reagent dictionary.
    """
    plateAndWell = ParseReagentInfo(reagentLine[1], expID)[0]
#    print('reagentline', reagentLine)
    if len(reagentLine) <3 or reagentLine[2] == 'DEFAULT':
        method = 'LC_W_Bot_Bot'
        #note: check if method exists should be performed within the subfunction, not here
#        print('method default', method)
    else:
        method = reagentLine[2]
#        print('method reagent', method)
    #IMPORTANT: SPREAD doesn't work right! It takes Method from the reaction (if default), not from the reagent!!!
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
#        for r in reagent:
#            plateDms = GetPlate(r['Plate'], expID)
#            r['Wells'] = ParseWells(r['Wells'], plateDms[1:])
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
        print('reagentInfo', reagentInfo)
        print('reagentRaw', reagentRaw)
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
        #append plate dictionary to the global location list for the reagent
    return reagent #return full detailed information about the reagent

    
def LineToList(line, configFileName, expID):
    if line:
        # if line[0][:1] == '%': #and if it is a comment ## (line[0][:1] == '#') or (line[0][:1] == '%')
        #     print(' '.join(line)) #join it back and print as it

        #note: experiment name
        if line[0] == 'NAME': #if we found an experiment name
            global expName
            expName = ' '.join(line[1:])
            DatabaseConnect()
            message = "UPDATE Experiments SET Experiment = " + "'" + expName + "'" + "WHERE ExpID = " + expID
            crsr.execute(message)
            DatabaseDisconnect()
            print('Experiment ID:', expID, '| Name: ', expName)

        #note: loading table
        elif line[0] == 'TABLE':
            global tableadded
            if not tableadded: #if the table file hasn't been added yet.
                tableadded = True
                tablefolder = 'tables' + os.sep
                print(line[0], 'file location: ', line[1])
                copyfile(tablefolder + line[1], 'esc' + os.sep + 'config' + expID + '.esc') #'tables' + os.sep +
#                except IOError:
#                    os.mkdir('esc')
#                    copyfile(tablefolder + line[1], 'esc' + os.sep + 'config' + expID + '.esc') #'tables' + os.sep +
                plateFile = open(tablefolder + line[1], "r")
                plateNicknames = {}
                plateIndexes = {}
                PlateFileParse(plateFile, plateIndexes, plateNicknames)
                DatabaseConnect()
                AddElements('PlateLocations', (plateNicknames, plateIndexes), expID)
                DatabaseDisconnect()


        #note: specifying reagents
        elif line[0] == 'COMPONENT':
            print('Component', line)
            reagentDict = ParseReagent(line[1:], expID)
            DatabaseConnect()
            print('reagentDict', reagentDict)
            AddElements('Reagents', reagentDict, expID)
            DatabaseDisconnect()

        #note: renaming plates
        elif line[0] == 'PLATE':
            plateLine = line[1:]
            DatabaseConnect()
            AddElements('PlateNicknames', plateLine, expID)
            DatabaseDisconnect()

        #note: defining a recipe
        elif line[0] == 'RECIPE':
            recipe = [expID, line[1]]
            ParseRecipe(configFileName, recipe)
            DatabaseConnect()
            AddElements('Recipe', recipe, expID)
            DatabaseDisconnect()

        #note: setting volume variables
        elif line[0] == 'VOLUME':
            try:
                float(line[2])
            except ValueError:
                sys.exit('Please check your volume format.') #IMPORTANT!! works only with the console-type app. won't work for a web server
            reagentList = [expID, line[1], line[2]]
            DatabaseConnect()
            AddElements('Volumes', reagentList, expID)
            DatabaseDisconnect()

        #note: loading information from file
        elif line[0] == 'LOAD':
            loadFile = open(line[1] + '.xls', "r")
            reagentPlate = line[2]
            reagentMethod = line[3]
            loadLines = loadFile.readlines()
            for r in range(1, len(loadLines)):
                lineList = loadLines[r].split()
                for c in range(1, len(lineList)):
                    rDict = {'Name' : lineList[c], 'Plate' : reagentPlate, 'Wells' : [(r, c)], 'Method': reagentMethod}
                    DatabaseConnect()
                    AddElements('Reagents', rDict, expID)
                    DatabaseDisconnect()

        #note: documentation string
        elif line[0] == '"""': #DOC
            configDict = []
            ParseDoc(configFileName, configDict)
#            print(configDict)
            DatabaseConnect()
            message = "UPDATE Experiments SET Comment = " + "'" + '\n'.join(configDict) + "'" + "WHERE ExpID = " + expID
            crsr.execute(message)
            DatabaseDisconnect()

        #note: making recipes
        elif line[0] == 'MAKE': #working with sets
            global testindex
            testindex += 1
            if len(line) == 5:
                options = line[4].lower()
            else:
                options = ''
            DatabaseConnect()
            recipeCall = line[1].split(':')
            recipe = recipeCall[0]
            if(len(recipeCall) > 1):
                rStrings = recipeCall[1].split(',')
            plateAndWells = line[2].split(':')
            message = 'SELECT Plate, Rows, Columns FROM (PlateNicknames NATURAL JOIN PlateLocations NATURAL JOIN Plates) WHERE Nickname = ' + '"' + plateAndWells[0] + '"' + ' and ExpID = ' + expID
            crsr.execute(message)
            dstPlateInfo = crsr.fetchone()
            if dstPlateInfo == None:
                message = 'SELECT Plate, Rows, Columns FROM (PlateLocations NATURAL JOIN Plates) WHERE (Plate = ' + '"' + plateAndWells[0] + '"' + ') and ExpID = ' + expID
                crsr.execute(message)
                dstPlateInfo = crsr.fetchone()
            dstPlateName = dstPlateInfo[0]
            dstPlateDms = dstPlateInfo[1:]
            dstPlateWells = ParseWells(plateAndWells[1], dstPlateDms)

            if line[3] != 'DEFAULT':
                method = line[3]
            else:
                method = 'LC_W_Bot_Bot'

            wellInfo = {'Name' : '', 'Plate' : dstPlateName, 'Wells' : dstPlateWells, 'Method' : method}
            AddElements('Reagents', wellInfo, expID)
            dstWellIDs = []
            for well in wellInfo['Wells']:
                crsr.execute('SELECT WellID from Wells WHERE ExpID = ' + expID + ' AND Plate = ' + '"' + wellInfo['Plate'] + '"' + ' AND Location = ' + '"' + str(well) + '"')
                dstWellIDs.append(crsr.fetchone()[0])
#            print('dstwellids', dstWellIDs)

            #IMPORTANT: this is the recipe parsing
            #note: SELECT Name, Volume FROM Recipes WHERE ExpID = (SELECT Max(ExpID) FROM Experiments) AND Column = 1;
            #todo: rewrite as 'Row' instead of column to slice the list other way
            maxRecipeCol = 'select max(Column) from Recipes where ExpID = ' + expID + ' and Recipe = ' + '"' + recipe + '"'
#            print(maxRecipeCol)
            crsr.execute(maxRecipeCol)
            a = crsr.fetchone()[0]
#            print('!!!', a)
            maxCol = int(a)
            trList = []
            for tr in range(1, maxCol + 1):
                if ':' not in line[1]:
                    message = 'SELECT Name, Volume FROM Recipes WHERE ExpID = ' + expID + ' AND Column = ' + str(tr) + ' ORDER BY Row ASC'
                    crsr.execute(message)
                    info = crsr.fetchall()
                else: #(Subrecipe = "coffee" OR Subrecipe = "lemonade")
                    info = []
                    for name in rStrings:
                        subrName = '"' + name + '"'
                        message = 'SELECT Name, Volume FROM (Recipes NATURAL JOIN Subrecipes) WHERE ExpID = ' + expID + ' AND Column = ' + str(tr) + ' AND Subrecipe = ' + subrName
                        crsr.execute(message)
                        strInfo = crsr.fetchone()
#                        print('strinfo', strInfo)
                        info.append(strInfo)

#                print('info', info)
                trList.append(info)

            trNo = 0
            for trLine in trList:
                trID = GetMaxID('transfer', expID)
#                print('trLine', trLine)
                for i in range (0, len(trLine)): #works only if no keywords
                    trNo += 1
                    rName = trLine[i][0]
                    if ':' in rName:
                        abc = ParseReagentInfo(rName, expID)
#                        print('abc', abc)
                        #bug: it works if the reagent is in one well only!!!! will cut off everything but first if not!!!
    #                    for well in info['Wells']: #note: add somewhere here after the thing with wells is fixed
                        well = abc[0]['Wells'][0]
                        abc[0]['Method'] = 'LC_W_Bot_Bot'
                        abc[0]['Name'] = ''
#                        print(abc[0])
                        #IMPORTANT: check if the well exists before adding it to DB
#                        try:
#                            crsr.execute()
                        #{'Plate': 'PL7', 'Name': 'PCR_Mx', 'Wells': [(1, 1)], 'Method': 'LC_W_Lev_Bot'} info
                        #call AddElements on wells and return a reagent ID and a well ID
                        wellCheck = 'SELECT WellID from Wells WHERE Location = ' + '"' + str(well) + '"' + ' AND Plate = ' + '"' + abc[0]['Plate'] + '"' + ' AND ExpID = ' + expID
                        crsr.execute(wellCheck)
                        wlID = crsr.fetchone()
#                        print('wellcheck', wellCheck, wlID)
                        if wlID == None:
                            #todo: check if these wells exist. if not, add them
#                            print('abc[0]', abc[0])
                            #IMPORTANT!!!
                            #                            print(abc[0])
                            AddElements('Reagents', abc[0], expID)
                            rMessage = 'SELECT WellID from Wells WHERE Location = ' + '"' + str(well) + '"' + ' AND Plate = ' + '"' + abc[0]['Plate'] + '"' + ' AND ExpID = ' + expID
                            #                            print('rms', rMessage)
                            crsr.execute(rMessage)
                            srcWellID = crsr.fetchone()[0]
                        else:
                            srcWellID = wlID[0]
                    else:
                        srcSelect = 'SELECT WellID FROM (ReagentNames NATURAL JOIN Reagents) WHERE ExpID = ' + expID + ' AND Name = ' + '"' + rName + '"'
#                        print(srcSelect)
                        crsr.execute(srcSelect)
                        srcWellID = crsr.fetchone()[0]
                    rVolume = VolumeToNumber(trLine[i][1], expID)
                    tips = SplitAmount(rVolume, expID)

                    if line[3] == 'DEFAULT':
                        crsr.execute('SELECT Method from Reagents WHERE ExpID = ' + expID + ' AND WellID = ' + str(srcWellID))
                        method = crsr.fetchone()[0]
                    else:
                        method = line[3]
                    trMessage = 'INSERT INTO Transfers VALUES(' + str(trID) + ', ' + str(expID) + ', ' + str(trNo) + ', ' + str(srcWellID) + ', ' + str(dstWellIDs[i]) + ', ' + rVolume + ', ' + '"' + method + '"' + ', ' +  '"' + str(tips) + '"' + ', ' + '"' + options + '")'
#                    print(trMessage)
                    crsr.execute(trMessage)
                    conn.commit()

            DatabaseDisconnect()

        #note: transferring or spreading a reagent
        elif (line[0] == 'TRANSFER') or (line[0] == 'SPREAD'):
            global testindex
            testindex += 1
            if line[0] == 'TRANSFER':
                destination = 'Transfer'
            else:
                destination = 'Distribute'

            if len(line) == 6:
                options = line[5]
            else:
                options = ''
            srcReagentInfo = ['', line[1], line[4]]
            srcReagentDict = ParseReagent(srcReagentInfo, expID)

            plate = GetPlate(srcReagentDict['Plate'], expID)
            srcReagentDict['Volume'] = VolumeToNumber(line[3], expID)

            dstReagentInfo = ['', line[2], line[4]]
            dstReagentDict = ParseReagent(dstReagentInfo, expID)

            plate = GetPlate(dstReagentDict['Plate'], expID)
            dstReagentDict['Volume'] = VolumeToNumber(line[3], expID)

            transferID = GetMaxID('transfer', expID)

            DatabaseConnect()
            AddElements(destination, [transferID, srcReagentDict, dstReagentDict, options], expID)
            DatabaseDisconnect()
        # else:
        #     print('other: ', line) #mark everything else as 'other', so when the script runs, it's obvious what's got left out


def ParseConfigFile():
    parser = argparse.ArgumentParser(description = 'Transfer liquids') #create the new argument parser for the command line arguments
    parser.add_argument('config_file_name', type = argparse.FileType('r'), default = sys.stdin, help = 'Config file')
    parser.add_argument('--log', type = argparse.FileType('w'), default = sys.stdout, help = 'Log file') #not used right now
    args = parser.parse_args()
    DatabaseConnect()
    global expID
    expID = str(int(ExecuteCommand('SELECT max(ExpID) FROM Experiments;')[0]) + 1)
    ParseFile(args.config_file_name, expID)
    if not args.log:
        print('hey!')

def ParseFile(filename, expID):
    """
    ParseFile reads the file string by string
    """
    global expName
    global setList
    setList = []
    expName = 'NoName'
    values = expID + ", '" + expName + "'" + ", ' '"
    InsertValues(values, 'Experiments')
    DatabaseDisconnect()
    line = filename.readline()
    global tableadded
    tableadded = False
    global testindex
    testindex = 0
    while line != '':
        oneline = line.split()
        LineToList(oneline, filename, expID)
        line = filename.readline()
    return testindex


def DatabaseConnect():
    global conn
    conn = sqlite3.connect('parpar.db')
    global crsr
    crsr = conn.cursor()

def DatabaseDisconnect():
    conn.commit()
    crsr.close()
    conn.close()

def GetMaxID(name, expID):
    """
    Gets maximum ID for given elements
    """
    if name == 'reagent':
        command = 'SELECT Max(ReagentID) FROM Reagents'
    elif name == 'well':
        command = 'SELECT Max(WellID) FROM Wells'
    elif name == 'transfer':
        command = 'SELECT Max(TransferID) FROM Transfers'
    crsr.execute(command + ' WHERE ExpID = ' + expID)
    for row in crsr:
        if row[0] == None:
            return 1
        else:
            return row[0] + 1

def AddElements(destName, info, expID):
    """
    Adds provided elements to the destination database
    """
    #note: when adding reagents, check if the wells exist first. If yes, add only a name to a reagent.
    if destName == 'Reagents':
        reagentID = str(GetMaxID('reagent', expID))
        for well in info['Wells']:
            wellID = str(GetMaxID('well', expID))
            wellInfo = wellID + ", " + expID + ", " + "'" + info['Plate'] + "'" + ", " + "'" + str(well) + "'"
            InsertValues(wellInfo, 'Wells')
            reagentInfo = reagentID + ", " + expID + ", " + wellID + ", " + "'" + info['Method'] + "'"
            InsertValues(reagentInfo, 'Reagents')
        if info['Name'] != '' :
            reagentNameInfo = reagentID + ", " + expID + ", " + "'" + info['Name'] + "'"# + ", " + "'" + info['Method'] + "'"
            InsertValues(reagentNameInfo, 'ReagentNames')

    elif (destName == 'Transfer') or (destName == 'Distribute'):
        transferID = str(info[0])
        srcDict = info[1]
        dstDict = info[2]
        options = info[3]

        if destName == 'Distribute':
            n = 0
            srcWellList = []
            for i in range(0, len(dstDict['Wells'])):
                srcWellList.append(srcDict['Wells'][n])
                i+=1
                if n == len(srcDict['Wells']) - 1:
                    n = 0
                else:
                    n+=1
            srcDict['Wells'] = srcWellList

        assert(len(srcDict['Wells']) == len(dstDict['Wells'])), 'Amount of source and destination wells should be equal'
        trNo = 0
        #for x in zip(cycle(src), dst): print("FROM %s TO %s WITH BLABLA" % x)
        for i in range(0, len(srcDict['Wells'])):
            trNo += 1
            crsr.execute('SELECT WellID from Wells WHERE ExpID = ' + expID + ' AND Plate = ' + '"' + srcDict['Plate'] + '"' + ' AND Location = ' + '"' + str(srcDict['Wells'][i]) + '"')
            try:
                srcWellID = str(crsr.fetchone()[0])
            except TypeError:
                srcWellID = str(GetMaxID('well', expID))
                srcWellInfo = srcWellID + ", " + expID + ", " + "'" + srcDict['Plate'] + "'" + ", " + "'" + str(srcDict['Wells'][i]) + "'"
                InsertValues(srcWellInfo, 'Wells')
            selection = 'SELECT WellID from Wells WHERE ExpID = ' + expID + ' AND Plate = ' + '"' + dstDict['Plate'] + '"' + ' AND Location = ' + '"' + str(dstDict['Wells'][i]) + '"'
            crsr.execute(selection)
            try:
                dstWellID = str(crsr.fetchone()[0])
            except TypeError:
                dstWellID = str(GetMaxID('well', expID))
                dstWellInfo = dstWellID + ", " + expID + ", " + "'" + dstDict['Plate'] + "'" + ", " + "'" + str(dstDict['Wells'][i]) + "'"
                InsertValues(dstWellInfo, 'Wells')

            tipsAmount = SplitAmount(srcDict['Volume'], expID)
            transferInfo = transferID + ", " + expID + ", " + str(i + 1) + ", " + srcWellID + ", " + dstWellID + ", " + srcDict['Volume'] + ", " + "'" + srcDict['Method'] + "'"  + ", " + "'" + str(tipsAmount) + "'"  + ", " + "'" + options + "'"
            InsertValues(transferInfo, 'Transfers')

    elif destName == 'Recipe':
        recipe = info[1]
        row = 1
#        print('!!! recipe', info)
        for element in info[2:]:
            column = 1
            if type(element[0]) == str:
                subrecipe = element[0]
                subrecipeInfo = expID + ", '" + recipe + "', " + str(row) + ", '" + subrecipe + "'"
                InsertValues(subrecipeInfo, 'Subrecipes')
                recipeElement = element[1:]
            else:
                recipeElement = element

#            print(element)
            for reagent in recipeElement:
                name = reagent[0]
                volume = reagent[1]
                recipeInfo = expID + ", '" + recipe + "', " + str(row) + ", " + str(column) + ", '" + name + "', '" + volume + "'"
                InsertValues(recipeInfo, 'Recipes')
                column += 1
            row += 1

    elif destName == 'Volumes':
        VolumeName = info[1]
        VolumeValue = info[2]
        volumeInfo = expID + ", '" + VolumeName + "', '" + VolumeValue + "'"
        InsertValues(volumeInfo, 'Volumes')

    elif destName == 'PlateLocations': # Plate, ExpID, FactoryName, Location
        plates = info[0]
        indexes = info[1]
        for key in plates.keys():
            location = indexes[key]
            grid = location[0]
            site = location[1]
            values = "'" + key + "'" + ", " + expID  + ', ' + "'" + plates[key] + "'" + ', ' + "'" + str(grid) + "'" + ', ' + "'" + str(site) + "'"
            InsertValues(values, destName)

    elif destName == 'PlateNicknames': # Nickname, ExpID, Plate
        values = "'" + info[0] + "'" + ", " + expID  + ', ' + "'" + info[1] + "'"
        InsertValues(values, destName)

def InsertValues(values, dbName):
    """
    Inserts into a given database given values
    """
    message = 'insert into ' + dbName + ' values(' + values + ')'
    crsr.execute(message)
    conn.commit()

def PrintDB(c, dbName):
    """
    Outputs the table items to the console
    """
    c.execute('select * from ' + dbName)
    for row in c:
        print(row)

def ExecuteCommand(command):
    """
    Executes the command on the database
    """
    crsr.execute(command)
    message = crsr.fetchone()
    return message

def VolumeToNumber(volume, expID):
    """
    Checks if the volume specified is number. If not, goes to the database and grabs the number value corresponding to the volume name.
    """
    try:
        int(volume)
        return volume
    except ValueError:
        message = 'SELECT VolumeValue FROM Volumes WHERE VolumeName = "' + volume + '" AND ExpID = ' + expID
        volume = ExecuteCommand(message)[0]
        return volume

def SplitAmount(rawAmount, expID):
    """
    Splitting the volume if it is more than the maximum amount allowed on the robot
    """
    global maxAm
#    convertedAmount = VolumeToNumber(rawAmount, expID)
    splitAmount = rawAmount.split('.')
    if len(splitAmount) > 1: # works for small volumes only
        amount = float(rawAmount)
    else:
        amount = int(rawAmount)
    if amount < maxAm:
        return([amount, 1])
    times = amount / int(maxAm)
    left = amount - int(maxAm * times)
    if left > 0:
        tipsNeeded = times + 1
        newAmount = [maxAm, tipsNeeded, left]
        return newAmount
    else:
        tipsNeeded = times
        newAmount = [maxAm, tipsNeeded]
        return newAmount

if __name__ == '__main__':
    ParseConfigFile()
    print('Experiment ID: ', expID)
    parpar.LiquidTransfer(expID, robotTips)
    wash = parpar.Wash()
    parpar.AppendToRobotCfg(expID, wash)
    print('Done. Check config.')
