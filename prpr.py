           
# prpr.py, a part of PR-PR (previously known as PaR-PaR), a biology-friendly language for liquid-handling robots
# Author: Nina Stawski, nstawski@lbl.gov, me@ninastawski.com
# Copyright 2012-2013, Lawrence Berkeley National Laboratory
# http://github.com/JBEI/prpr/blob/master/license.txt

__author__ = 'Nina Stawski'
__version__ = '1.1'

import os
import sqlite3

class DatabaseHandler:
    """
    Pulls all experiment info from the database and calls the appropriate parser depending on the platform
    """
    def __init__(self, expID):
        self.conn = sqlite3.connect('prpr.db')
        self.crsr = self.conn.cursor()
        self.expID = str(expID)
        self.getExperimentInfo()
        self.mfWellLocations = {}
        self.mfWellConnections = {}
        self.getMFinfo()
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

    def getExperimentInfo(self):
        info = self.getOne('SELECT * from Experiments WHERE ExpID = ' + self.expID)
        self.maxTips = info[1]
        self.maxVolume = info[2]
        self.platform = info[3]

    def getTransfer(self, actionID, type):
        if type == 'transfer':
            command = 'SELECT srcWellID, dstWellID, Volume, Method FROM Transfers WHERE ExpID = ' + self.expID + ' AND ActionID = ' + str(actionID) + ' ORDER BY trOrder ASC'
        elif type == 'command':
            command = 'SELECT Command, Options, ActionID, trOrder FROM Commands WHERE ExpID = ' + self.expID + ' AND ActionID = ' + str(actionID) + ' ORDER BY trOrder ASC'
        self.crsr.execute(command)
        transferElements = self.crsr.fetchall()
        print('transferElements___', transferElements)
        transfer = {'type' : type, 'info' : []}
        for element in transferElements:
            if type == 'transfer':
                srcWell = self.getWell(element[0])
                dstWell = self.getWell(element[1])
                if self.platform == "tecan":
                    volume = eval(element[2])
                    method = element[3]
                    transfer['info'].append({ 'source' : srcWell, 'destination' : dstWell, 'volume' : volume, 'method' : method })
                else:
                    times = element[2]
                    wait = element[3]
                    transfer['info'].append({ 'source' : srcWell, 'destination' : dstWell, 'times' : times, 'wait' : wait })
            if type == 'command':
                if element[0] == 'mix':
                    mixOptions = element[1].split('x')
                    m = self.getAll('SELECT Location FROM CommandLocations WHERE ActionID = ' + str(actionID), order='ORDER BY trOrder ASC')
                    for well in m:
                        w = self.getWell(well)
                        transfer['info'].append({'command' : 'mix', 'volume' : mixOptions[0], 'times' : mixOptions[1], 'target' : w })
                elif element[0] == 'move':
                    trOrder = element[-1]
                    m = self.getAll('SELECT Location FROM CommandLocations WHERE ActionID = ' + str(actionID) + ' AND trOrder = ' + str(trOrder), order='ORDER BY trOrder ASC')
                    for move in m:
                        transfer['info'].append({'command' : 'move', 'location' : move})
                        
                elif element[0] == 'message' or element[0] == 'comment':
                    command = element[0]
                    message = element[1]
                    transfer['info'].append({'command' : command, 'message' : message})
        return transfer

    def getMFinfo(self): #mfWellLocations, mfWellConnections
        wells = self.getAll('SELECT DISTINCT WellName FROM mfWellLocations WHERE ExpID = ' + self.expID)
        for well in wells:
            location = self.getOne('SELECT WellCoords from mfWellLocations WHERE WellName = "' + well + '" AND ExpID = ' + self.expID)[0]
            connections = self.getAll('SELECT ConnectionName FROM mfWellConnections WHERE WellName = "' + well + '" AND ExpID = ' + self.expID)
            self.mfWellConnections[well] = connections
            self.mfWellLocations[well] = tuple(int(x) for x in location.split(','))

    def getWell(self, wellID):
        w = self.getOne('SELECT Plate, Location FROM Wells WHERE WellID = ' + str(wellID))
        plateName = w[0]
        if self.platform == 'tecan':
            wellLocation = eval(w[1])
        else:
            wellLocation = w[1]
        plateDimensions = self.getOne('SELECT Rows, Columns FROM Plates NATURAL JOIN PlateLocations WHERE Plate = "' + plateName + '"')
        plateLocation = self.getOne('SELECT Grid, Site FROM PlateLocations WHERE Plate = "' + plateName + '"')
        return { 'well' : wellLocation, 'plateDimensions' : plateDimensions, 'plate' : plateLocation }

    def getOne(self, message):
        self.crsr.execute(message + ' AND ExpID = ' + self.expID)
        row = self.crsr.fetchone()
        return row

    def getAll(self, message, order=''):
        self.crsr.execute(message + ' AND ExpID = ' + self.expID + ' ' + order)
        all = []
        for item in self.crsr.fetchall():
            all.append(item[0])
        return all

    def close(self):
        self.conn.commit()
        self.crsr.close()
        self.conn.close()

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


class Well:
    def __init__(self, dict_):
        self.plate = dict_['Plate']
        self.location = dict_['Location']


class Component:
#    method = 'LC_W_Bot_Bot'
    def __init__(self, dict_):
        self.name = dict_['name']
        self.location = dict_['location']
        self.shortLocation = dict_['location']
        if 'method' in dict_:
            self.method = dict_['method']
        else:
            self.method = 'empty'


class Plate:
    def __init__(self, plateName, factoryName, plateLocation, platform, dimensions=()):
        self.name = plateName
        self.factoryName = factoryName
        self.location = plateLocation
        if platform != 'human':
            db = DatabaseHandler.db('SELECT Rows, Columns from Plates WHERE FactoryName=' + '"' + factoryName + '"')
            self.dimensions = db[0]
        else:
            self.dimensions = dimensions


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


