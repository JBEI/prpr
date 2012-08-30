__author__ = 'Nina Stawski'
__version__ = '0.3'

import sqlite3
import os

def DatabaseConnect():
    global conn
    conn = sqlite3.connect('parpar.db')
    global crsr
    crsr = conn.cursor()

def DatabaseDisconnect():
    conn.commit()
    crsr.close()
    conn.close()

def CreateTables():

    DatabaseConnect()

    crsr.execute('create table Experiments(ExpID UNIQUE, maxTips, maxVolume)')
    crsr.execute('create table ExperimentInfo(ExpID UNIQUE, Name, Comment)')
    # Creating the table for wells, for convenient linking to them
    crsr.execute('create table Wells(ExpID, WellID, Plate, Location, PRIMARY KEY(ExpID, WellID, Plate, Location))')
    # Creating the table for reagents
    crsr.execute('create table Components(ExpID, ComponentID, WellID, PRIMARY KEY(ExpID, ComponentID, WellID))')
    crsr.execute('create table ComponentMethods(ExpID, ComponentID, Method, PRIMARY KEY(ExpID, ComponentID, Method))')
    crsr.execute('create table ComponentNames(ExpID, ComponentID, Name, PRIMARY KEY(ExpID, ComponentID, Name))')
    # Creating the table for plates
    crsr.execute('create table Plates(FactoryName UNIQUE, Rows, Columns)')
    crsr.execute('create table PlateLocations(ExpID, Plate, FactoryName, Grid, Site, PRIMARY KEY(ExpID, Plate))')
    crsr.execute('create table PlateNicknames(ExpID, Plate, Nickname, PRIMARY KEY(ExpID, Nickname))')
    crsr.execute('create table Volumes(ExpID, VolumeName, VolumeValue, PRIMARY KEY(ExpID, VolumeName))')
    crsr.execute('create table Recipes(ExpID, Recipe, Row, Column, Name, Volume, PRIMARY KEY(ExpID, Recipe, Row, Column))')
    crsr.execute('create table Subrecipes(ExpID, Recipe, Row, Subrecipe, PRIMARY KEY(ExpID, Recipe, Row, Subrecipe))')

    crsr.execute('insert into Experiments values(0, "", "");')

    crsr.execute('create table Methods(Method UNIQUE)')

    crsr.execute('create table Actions(ExpID, ActionID, Type, PRIMARY KEY(ExpID, ActionID));')
    crsr.execute('create table Transfers(ExpID, ActionID, trOrder, srcWellID, dstWellID, Volume, Method, PRIMARY KEY(ExpID, ActionID, trOrder, srcWellID, dstWellID));')
    crsr.execute('create table Commands(ExpID, ActionID, trOrder, Command, Options, PRIMARY KEY(ExpID, ActionID, trOrder));')
    crsr.execute('create table CommandLocations(ExpID, ActionID, Location, PRIMARY KEY(ExpID, ActionID, Location));')

    DatabaseDisconnect()
    
def UpdateMethods():
    methodFile = open('methodsInfo.txt', 'r')
    f = methodFile.readlines()
    for method in f:
        try:
            message = 'INSERT INTO Methods VALUES("' + method.strip() + '");'
            DatabaseConnect()
            crsr.execute(message)
        except sqlite3.IntegrityError:
            pass
        DatabaseDisconnect()

def UpdatePlates():
    plateFile = open('platesInfo.txt', 'r')
    f = plateFile.readlines()
    for plate in sorted(f):
        data = plate.split(',')
        name = data[0]
        print(name)
        dimensions = data[1]
        size = dimensions.split('x')
        try:
            message = 'INSERT INTO Plates VALUES("' + name + '",' + size[1] + ',' + size[0] + ');'
            DatabaseConnect()
            crsr.execute(message)
        except sqlite3.IntegrityError:
            DatabaseConnect()
            crsr.execute(message)
            message = 'UPDATE Plates SET Rows = ' + size[1] + ', Columns = ' + size[0] + '  WHERE FactoryName = ' + '"' + name + '"'
        DatabaseDisconnect()

def CreateFolders():
    os.mkdir('esc')
    os.mkdir('incoming')
    os.mkdir('logs')

CreateFolders()
CreateTables()
UpdatePlates()
UpdateMethods()
print('Done!')