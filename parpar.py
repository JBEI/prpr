#!/usr/bin/env python3.2
__author__ = 'Nina Stawski'
__version__ = '0.3'

import os
import sqlite3

class ParPar:
    wash = 'Wash(255,1,1,1,0,"2",500,"1.0",500,20,70,30,1,1,1000);'
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
        fileName = 'esc' + os.sep + 'config' + self.expID + '.esc'
        myfile = open(fileName, 'a', encoding='latin1')
        for line in self.robotConfig:
            myfile.write(line.rstrip() + '\r\n')
        myfile.close()

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
                                    action = element['command']
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
        tr = self.splitTransaction(transferList)
        for element in tr:
            for command in commandsList:

                trList = []
                z = max([x['volume'][1] for x in element])
                for n in range(0, z+1):
                    trList.append([])

                tipNumber = 1
                for e in element:
                    method = e['method']
                    if command == 'Aspirate':
                        wellInfo = e['source']
                    elif command == 'Dispense':
                        wellInfo = e['destination']
                    for i in range(0, e['volume'][1]):
                        trList[i].append({ 'command' : command, 'tipNumber' : tipNumber, 'wellInfo' : wellInfo, 'volume' : e['volume'][0], 'method' : method })
                    if len(e['volume']) == 3:
                        trList[e['volume'][1]].append({ 'command' : command, 'tipNumber' : tipNumber, 'wellInfo' : wellInfo, 'volume' : e['volume'][2], 'method' : method })
                    tipNumber += 1
                self.transactions.append(trList)

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

    def fillVolumesList(self, volumesDict):
        """
        Finalizes the list of volumes by adding zeroes where needed.
        """
        for l in range (0, 12):
            if l+1 not in volumesDict:
                volumesDict[l+1] = '0'
        volumesList = []
        for d in range (1, 13):
            volumesList.append(volumesDict[d])
        return volumesList

    def joinVolumesList(self, volumesList):
        """
        Creates the final list of volumes for aspirate / dispense commands
        """
        tipsEnc = 0
        for i in range(0, len(volumesList)):
            if volumesList[i] != '0':
                tipsEnc += self.getTipEncoding(i+1)
        volumesString = ','.join(volumesList)
        return volumesString, tipsEnc

class DatabaseHandler:
    def __init__(self, expID):
        self.conn = sqlite3.connect('parpar.db')
        self.crsr = self.conn.cursor()
        self.expID = str(expID)
        self.maxTips = self.getMaxTips()
        self.transfers = []
        self.getAllTransfers()
        self.close()

    def getAllTransfers(self):
        command = 'SELECT ActionID, Type FROM Actions WHERE ExpID = ' + self.expID + ' ORDER BY ActionID ASC'
        self.crsr.execute(command)
        self.allTransfers = self.crsr.fetchall()
        for t in range(0, len(self.allTransfers)):
            transfer = self.allTransfers[t]
            transferID = str(transfer[0])
            transferType = transfer[1]
            tr = self.getTransfer(transferID, transferType)
            self.transfers.append(tr)

    def getMaxTips(self):
        tips = self.getOne('SELECT maxTips from Experiments WHERE ExpID = ' + self.expID)
        return tips[0]

    def getTransfer(self, actionID, type):
        if type == 'transfer':
            command = 'SELECT srcWellID, dstWellID, Volume, Method FROM Transfers WHERE ExpID = ' + self.expID + ' AND ActionID = ' + str(actionID) + ' ORDER BY trOrder ASC'
        elif type == 'command':
            command = 'SELECT Command, Options FROM Commands WHERE ExpID = ' + self.expID + ' AND ActionID = ' + str(actionID) + ' ORDER BY trOrder ASC'
        self.crsr.execute(command)
        transferElements = self.crsr.fetchall()
        transfer = {'type' : type, 'info' : []}
        for element in transferElements:
            if type == 'transfer':
                srcWell = self.getWell(element[0])
                dstWell = self.getWell(element[1])
                volume = eval(element[2])
                method = element[3]
                transfer['info'].append({ 'source' : srcWell, 'destination' : dstWell, 'volume' : volume, 'method' : method })
            if type == 'command':
                if element[0] == 'mix':
                    mixOptions = element[1].split('x')
                    m = self.getAll('SELECT Location FROM CommandLocations WHERE ActionID = ' + str(actionID), order='ORDER BY trOrder ASC')
                    for well in m:
                        w = self.getWell(well[0])
                        transfer['info'].append({'command' : 'mix', 'volume' : mixOptions[0], 'times' : mixOptions[1], 'target' : w })
                elif element[0] == 'message' or element[0] == 'comment':
                    command = element[0]
                    message = element[1]
                    transfer['info'].append({'command' : command, 'message' : message})
        return transfer

    def getWell(self, wellID):
        w = self.getOne('SELECT Plate, Location FROM Wells WHERE WellID = ' + str(wellID))
        plateName = w[0]
        wellLocation = eval(w[1])
        plateDimensions = self.getOne('SELECT Rows, Columns FROM Plates NATURAL JOIN PlateLocations WHERE Plate = "' + plateName + '"')
        plateLocation = self.getOne('SELECT Grid, Site FROM PlateLocations WHERE Plate = "' + plateName + '"')
        return { 'well' : wellLocation, 'plateDimensions' : plateDimensions, 'plate' : plateLocation }

    def getOne(self, message):
        self.crsr.execute(message + ' AND ExpID = ' + self.expID)
        row = self.crsr.fetchone()
        return row

    def getAll(self, message, order=''):
        self.crsr.execute(message + ' AND ExpID = ' + self.expID + ' ' + order)
        all = self.crsr.fetchall()
        return all

    def close(self):
        self.conn.commit()
        self.crsr.close()
        self.conn.close()

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


if __name__ == '__main__':
    parpar = ParPar(310)
    print('Robot Config:')
    for element in parpar.robotConfig:
        print(element)