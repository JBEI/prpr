#!/usr/bin/env python3.2
__author__ = 'Nina Stawski'
import os
import sqlite3

#def GetReagent(expID, reagent):
#    location = ExecuteCommand('SELECT * FROM (Reagents NATURAL JOIN ReagentLocations) WHERE name = ' + '"' + reagent + '" AND ExpID = ' + expID)
#    return(location)
    
##from pyevo
def getTipEncoding(tipNumber):
    return 1 << (tipNumber - 1)

#def getMultiTipEncoding(numberOfTips):
#    encoding = 0
#    for i in range(1,1 + numberOfTips):
#        encoding += getTipEncoding(i)
#    return (encoding)

def getTipAmountString(tipNumber, amount):    
    param = ""
    for i in range(1,13):
        if i <= tipNumber:
            param += '"' + str(amount) + '",'
        elif (not i) == 12:
            param += ","
        else:
            param += "0,"
    return param

def getWellEncoding(wellsList,maxRows,maxColumns):
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
        
def Wash():
    command = 'Wash(255,1,1,1,0,"2",500,"1.0",500,20,70,30,1,1,1000);'
    return command

def Mix(tipNumber, gridAndSite, wellString, volumesString, mixOptions):
    command = 'Mix(' + str(tipNumber) + ',"LCWMX",' +\
              volumesString + ',' + str(gridAndSite) + ',1,"' +\
              wellString + '",' + mixOptions + ',0);'
    return command

def Command(action, tipNumber, gridAndSite, wellString, method, volumesString, mixOptions=''):
    assert (action == 'Aspirate' or action == 'Dispense'), 'You entered the wrong command. Check your script and try again'
    command = action + '(' + str(tipNumber) + ',"' +\
              method + '",' + volumesString + ',' +\
              str(gridAndSite) + ',1,"' + wellString +\
              '",0);'
    return command

def GetWell(wellID, expID):
    connection = sqlite3.connect('parpar.db')
    c = connection.cursor()
    c.execute('SELECT Plate, Location FROM Wells WHERE WellID = ' + str(wellID) + ' AND ExpID = ' + str(expID))
    for row in c:
        return [row[0], row[1]]

def GetPlate(plateName, expID):
    connection = sqlite3.connect('parpar.db')
    c = connection.cursor()
    command = 'SELECT FactoryName, Rows, Columns from (Plates NATURAL JOIN PlateLocations) WHERE Plate=' + '"' + plateName + '"' + ' AND ExpID = ' + str(expID)
    c.execute(command)
    for row in c:
        return row
        
def GetPlateLocation(plateName, expID):
    connection = sqlite3.connect('parpar.db')
    c = connection.cursor()
    command = 'SELECT Grid, Site from PlateLocations WHERE Plate=' + '"' + plateName + '"' + ' AND ExpID = ' + str(expID)
    print(command)
    c.execute(command)
    return c.fetchone()

def GetMaxTips(expID):
    connection = sqlite3.connect('parpar.db')
    c = connection.cursor()
    c.execute('SELECT maxTips from Experiments WHERE ExpID = ' + str(expID))
    maxTips = c.fetchone()
    return maxTips[0]
        
def GetAllTransfers(expID):
    connection = sqlite3.connect('parpar.db')
    c = connection.cursor()
    command = 'SELECT ActionID, Type FROM Actions WHERE ExpID = ' + str(expID) + ' ORDER BY ActionID ASC'
    c.execute(command)
    allTransfers = c.fetchall()
    connection.close()
    return allTransfers

def GetTransfer(trID, expID):
    connection = sqlite3.connect('parpar.db')
    c = connection.cursor()
    command = 'SELECT srcWellID, dstWellID, Volume, Method FROM Transfers WHERE ExpID = ' + str(expID) + ' AND ActionID = ' + str(trID) + ' ORDER BY trOrder ASC'
    c.execute(command)
    transferElements = c.fetchall()
    connection.close()
    return transferElements

def GetCommand(trID, expID):
    connection = sqlite3.connect('parpar.db')
    c = connection.cursor()
    command = 'SELECT Command, Options FROM Commands WHERE ExpID = ' + str(expID) + ' AND ActionID = ' + str(trID) + ' ORDER BY trOrder ASC'
    c.execute(command)
    transferElements = c.fetchall()
    connection.close()
    return transferElements
        
def TransactionToList(expID, transactionID, wellInfo, wellList, method):
    connection = sqlite3.connect('parpar.db')
    c = connection.cursor()
    c.execute('SELECT * FROM Wells WHERE WellID = ' + str(wellInfo[0]) + ' AND ExpID = ' + expID)
    for row in c:
        wellList.append([transactionID, row[2], row[3], wellInfo[1], method])
    return wellList

def CheckIfWellsAreConsequent(well1, well2):
    if int(well1[1]) == int(well2[1]):
        if int(well1[0]) == (int(well2[0]) - 1):
            return True
        else:
            return False
    else:
        return False

def LiquidTransfer(expID):
    maxTips = GetMaxTips(expID)
    allTransfers = GetAllTransfers(expID)
    print('111', allTransfers)
    wash = Wash()
    commandsList = ('Aspirate', 'Dispense')
    for transfer in allTransfers:
        trID = transfer[0]
        trType = transfer[1]
        if trType == 'transfer':
            els = GetTransfer(trID, expID)
            if len(els) > maxTips:
                for l in range(0, len(els), maxTips):
                    cutEls = els[l:l+maxTips]
                    for e in range(0, len(cutEls)):
                        cutEls[e] = createTransactionDict(cutEls[e], expID)
                    AppendToRobotCfg(expID, wash)
                    for command in commandsList:
                        volumesList = []
                        listOfWells = []
                        startWell = 0
                        tipNum = 1
                        trCount = 0
                        ConstructTransaction(command, cutEls, trCount, tipNum, volumesList, startWell, listOfWells, expID)
            else:
                for e in range(0, len(els)):
                    els[e] = createTransactionDict(els[e], expID)
                for command in commandsList:
                    volumesList = []
                    listOfWells = []
                    startWell = 0
                    tipNum = 1
                    trCount = 0
                    ConstructTransaction(command, els, trCount, tipNum, volumesList, startWell, listOfWells, expID)

        if trType == 'command':
            cmd = GetCommand(trID, expID)
            for c in cmd:
                if c[0] == 'mix':
                    mixOptions = c[1].split('x')
                    mixString = CreateMixString(volumesString[0], mixOptions[0])
                    mix = Mix(volumesString[1], PlateGridAndSite, WellEncoding, mixString, mixOptions[1])
                    AppendToRobotCfg(expID, mix)



#            for element in els:
#                srcWellID = element[0]
#                dstWellID = element[1]
#                volume = element[2]
#                print( srcWellID, dstWellID, volume, '::' )


#        transferList = []
#        for row in transfer:
#            trDict = FillWellCoordinates(row)
#            transferList.append(trDict)
#
#        wash = Wash()
#        commandsList = ('Aspirate', 'Dispense')
#
#        trListLen = len(transferList)
##        print('trl', transferList[0])
#        if trListLen > robotTips:
#            for l in range(0, trListLen, robotTips):
#                cutTransferList = transferList[l:l+robotTips]
##                print(cutTransferList)
#                AppendToRobotCfg(expID, wash)
#                for command in commandsList:
#                    volumesList = []
#                    listOfWells = []
#                    startWell = 0
#                    tipNum = 1
#                    trCount = 0
#                    ConstructTransaction(command, cutTransferList, trCount, tipNum, volumesList, startWell, listOfWells)
#        else:
#            AppendToRobotCfg(expID, wash)
#            for command in commandsList:
#                volumesList = []
#                listOfWells = []
#                startWell = 0
#                tipNum = 1
#                trCount = 0
#                ConstructTransaction(command, transferList, trCount, tipNum, volumesList, startWell, listOfWells)

def FillWellCoordinates(transferList):
    srcWellCoords = GetWell(transferList[2], transferList[1])
    dstWellCoords = GetWell(transferList[3], transferList[1])

    trDict = {'trID' : transferList[0], 'expID' : transferList[1], 'srcPlate' : srcWellCoords[0], 'srcWell' : srcWellCoords[1], 'dstPlate' : dstWellCoords[0], 'dstWell' : dstWellCoords[1], 'method' : transferList[5], 'volume' : transferList[6], 'options' : transferList[7]}

    return trDict

def UpdateTransferParameters(trDict, listOfWells):
    global srcWellEncoding
    global dstWellEncoding
    global srcPlateGridAndSite
    global dstPlateGridAndSite
    global srcPlateDms
    global dstPlateDms
    global srcWellBit
    global dstWellBit
    global method
    global options

    expID = trDict['expID']

    #source
#    print(trDict)
    srcPlateLoc = GetPlateLocation(trDict['srcPlate'], expID)
    srcPlateDms = GetPlate(trDict['srcPlate'], expID)[1:]
    srcWell = eval(trDict['srcWell'])
    srcPlateGridAndSite = str(srcPlateLoc[0]) + ',' + str(srcPlateLoc[1])
    srcWellBit = srcWell
    srcWellEncoding = getWellEncoding(listOfWells, int(srcPlateDms[0]), int(srcPlateDms[1]))

    #destination
    dstPlateLoc = GetPlateLocation(trDict['dstPlate'], expID)
    dstPlateDms = GetPlate(trDict['dstPlate'], expID)[1:]
    dstWell = eval(trDict['dstWell'])
    dstPlateGridAndSite = str(dstPlateLoc[0]) + ',' + str(dstPlateLoc[1])
    dstWellBit = dstWell
    dstWellEncoding = getWellEncoding(listOfWells, int(dstPlateDms[0]), int(dstPlateDms[1]))

    method = trDict['method']

#    dstWellEncoding = getWellEncoding(int(dstWell[1]), int(dstWell[0]), int(dstPlateDms[0]), int(dstPlateDms[1]))

    transferParameters = { 'srcLoc' : srcPlateGridAndSite, 'dstLoc' : dstPlateGridAndSite, 'srcWell' : srcWellEncoding, 'dstWell' : dstWellEncoding, 'method' : method}

#    return(transferParameters)

def createTransactionDict(transaction, expID):
    srcw = str(transaction[0])
    dstw = str(transaction[1])
    volume = eval(transaction[2])
    method = transaction[3]

    connection = sqlite3.connect('parpar.db')
    c = connection.cursor()
    command = 'SELECT Plate, Location FROM Wells WHERE ExpID = ' + str(expID) + ' AND WellID = ' + srcw
    c.execute(command)
    srcInfo = c.fetchone()
    print('2222', srcInfo, command)
    srcPlate = srcInfo[0]
    srcWell = srcInfo[1]

    command = 'SELECT Plate, Location FROM Wells WHERE ExpID = ' + str(expID) + ' AND WellID = ' + dstw
    c.execute(command)
    dstInfo = c.fetchone()
    dstPlate = dstInfo[0]
    dstWell = dstInfo[1]
    connection.close()

    dict = {
        'srcWell' : srcWell,
        'srcPlate' : srcPlate,
        'dstPlate' : dstPlate,
        'dstWell' : dstWell,
        'volume' : volume,
        'expID' : expID,
        'method' : method
    }

    print(dict)

    return dict

def ConstructTransaction(action, transferList, trCount, tipNum, volumesList, startWell, listOfWells, expID):
    """
    Creating the aspirate / dispense strings from the list of transfers
    """
    global srcWellEncoding
    global dstWellEncoding
    global srcPlateGridAndSite
    global dstPlateGridAndSite
    global srcPlateDms
    global dstPlateDms
    global method
    global trID
    global trDict
    global options

    if trCount < len(transferList):
        if tipNum == 1:
            trDict = transferList[trCount]
            UpdateTransferParameters(trDict, listOfWells)
            tipNum+=1

        else:
            trDict = transferList[trCount]
        expID = trDict['expID']
        volume = trDict['volume']
        srcWellBit = eval(trDict['srcWell'])
        dstWellBit = eval(trDict['dstWell'])

#        print(trDict['srcPlate'])
#        print(trDict['dstPlate'])
        #check if transactionID is the same with previous element in the list, or different
        #if different, end volume list and pass it to the create aspirate function (and remember the position we were at, we will need it for dispense)
        nosplit = CheckTransaction(transferList, trCount, action)
        if nosplit == True:
            volumesList.append('"' + str(volume[0]) + '"')
            if action == 'Aspirate':
                listOfWells.append(srcWellBit)
            elif action == 'Dispense':
                listOfWells.append(dstWellBit)
            tipNum += 1
        else:
            volumesList = FillVolumesList(volumesList, startWell)
#            print(volumesList)
#            startWell = trCount
#            startWell = len(volumesList) + startWell
            volumesString = JoinVolumesString(volumesList)
#            startWell = trCount
#            AppendToRobotCfg(expID, wash)

            if action == 'Aspirate':
                PlateGridAndSite = srcPlateGridAndSite
                WellEncoding = getWellEncoding(listOfWells, int(srcPlateDms[0]), int(srcPlateDms[1]))
            elif action == 'Dispense':
                PlateGridAndSite = dstPlateGridAndSite
                WellEncoding = getWellEncoding(listOfWells, int(dstPlateDms[0]), int(dstPlateDms[1]))

            command = Command(action, volumesString[1], PlateGridAndSite, WellEncoding, method, volumesString[0])
            AppendToRobotCfg(expID, command)


#            dispense = Command('Dispense', volumesString[1], dstPlateGridAndSite, dstWellEncoding, method, volumesString[0])
#            AppendToRobotCfg(expID, dispense)
            #todo: aspirate and dispense have problems stacking

            del volumesList[:]
            del listOfWells[:]
#            startWell = trCount
            volumesList.append('"' + str(volume[0]) + '"')
            if action == 'Aspirate':
                listOfWells.append(srcWellBit)
            elif action == 'Dispense':
                listOfWells.append(dstWellBit)
            tipNum = 1
            startWell = trCount
        trCount += 1
        ConstructTransaction(action, transferList, trCount, tipNum, volumesList, startWell, listOfWells, expID)

    else:
        options = ''
        UpdateTransferParameters(trDict, listOfWells)
        volumesList = FillVolumesList(volumesList, startWell)
        volumesString = JoinVolumesString(volumesList)
#        AppendToRobotCfg(expID, wash)

        if action == 'Aspirate':
            PlateGridAndSite = srcPlateGridAndSite
            WellEncoding = getWellEncoding(listOfWells, int(srcPlateDms[0]), int(srcPlateDms[1]))
        elif action == 'Dispense':
            PlateGridAndSite = dstPlateGridAndSite
            WellEncoding = getWellEncoding(listOfWells, int(dstPlateDms[0]), int(dstPlateDms[1]))

        command = Command(action, volumesString[1], PlateGridAndSite, WellEncoding, method, volumesString[0])
        AppendToRobotCfg(expID, command)
        if options != '':
            if action == 'Dispense':
                optionList = options.split(',')
                for option in optionList:
                    sepdOption = option.split(':')
                    if sepdOption[0] == 'MIX':
                        mixOptions = sepdOption[1].split('x')
                        mixString = CreateMixString(volumesString[0], mixOptions[0])
                        mix = Mix(volumesString[1], PlateGridAndSite, WellEncoding, mixString, mixOptions[1])
                        AppendToRobotCfg(expID, mix)
        tipNum = 1

#        dispense = Command('Dispense', volumesString[1], dstPlateGridAndSite, dstWellEncoding, method, volumesString[0])
#        AppendToRobotCfg(expID, dispense)

def CreateMixString(volumesString, newVolume):
    ms = volumesString.split(',')
    for i in range(0, len(ms)):
        if ms[i] != '0':
            ms[i] = '"' + newVolume + '"'
    volumesString = JoinVolumesString(ms)
    return volumesString[0]

def CheckTransaction(transferList, trCount, action):
    """
    Checks if the current transaction should be split into separate transactions. Basically checks that wells are consequent.
    """
    if action == 'Aspirate':
        well = 'srcWell'
    elif action == 'Dispense':
        well = 'dstWell'
    if trCount == 0:
        return True
    else:
        tr1 = transferList[trCount]
        tr0 = transferList[trCount - 1]

        a = CheckIfWellsAreConsequent(eval(tr0[well]), eval(tr1[well]))
#        if (int(eval(tr1[well])[1]) == int(eval(tr0[well])[1]) + 1) and (int(eval(tr1[well])[0]) == int(eval(tr0[well])[0]) + 1):
#            return True
#        else:
#            return False
        return(a)

def FillVolumesList(volumesList, startWell):
    """
    Finalizes the list of volumes by adding zeroes where needed.
    """
    if(startWell > 0):
        for i in range(0, startWell):
            volumesList.insert(0, '0')
    listSize = len(volumesList)
    if(listSize < 12):
        rest = 12 - listSize
        for i in range(0, rest):
            volumesList.append('0')
    return(volumesList)

def JoinVolumesString(volumesList):
    """
    Creates the final list of volumes for aspirate / dispense commands
    """
    tipsEnc = 0
    for i in range(0, len(volumesList)):
        if(volumesList[i] != '0'):
            tipsEnc += getTipEncoding(i+1)
    volumesString = ','.join(volumesList)
    return(volumesString, tipsEnc)

def SplitWells(multWells):
    sepdWells = {}
    for well in multWells:
        if (well[1] in sepdWells.keys()):
            sepdWells[well[1]].append(well)
        else:
            sepdWells[well[1]] = []
            sepdWells[well[1]].append(well)
    return(sepdWells)
    
def AppendToRobotCfg(expID, line):
    fileName = 'esc' + os.sep + 'config' + str(expID) + '.esc'
    try:
        myfile = open(fileName, 'a', encoding='latin1')
    except IOError:
        os.mkdir('esc')
        myfile = open(fileName, 'a', encoding='latin1')
    myfile.write(line.rstrip() + '\r\n')
    myfile.close()

def AppendToLog(expID, line):
    logName = 'logs' + os.sep + 'exp' + str(expID) + '.log'
    try:
        myfile = open(logName, 'a')
    except IOError:
        os.mkdir('esc')
        myfile = open(logName, 'a')
    myfile.write(line.rstrip() + '\r\n')
    myfile.close()