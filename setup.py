__author__ = 'Nina Stawski'
__version__ = '0.32'

import sqlite3
import os
import stat

def DatabaseConnect():
    global conn
    conn = sqlite3.connect('prpr.db')
    global crsr
    crsr = conn.cursor()

def DatabaseDisconnect():
    conn.commit()
    crsr.close()
    conn.close()

def CreateTables():

    DatabaseConnect()

    #Experiment info
    crsr.execute('create table Experiments(ExpID UNIQUE, maxTips, maxVolume, Platform)')
    crsr.execute('create table ExperimentInfo(ExpID UNIQUE, Name, Comment)')

    #Methods
    crsr.execute('create table Methods(Method UNIQUE)')
    crsr.execute('create table DefaultMethod(Method Unique)')

    #Wells
    crsr.execute('create table Wells(ExpID, WellID, Plate, Location, PRIMARY KEY(ExpID, WellID, Plate, Location))')

    #Reagents
    crsr.execute('create table Components(ExpID, ComponentID, WellID, PRIMARY KEY(ExpID, ComponentID, WellID))')
    crsr.execute('create table ComponentMethods(ExpID, ComponentID, Method, PRIMARY KEY(ExpID, ComponentID, Method))')
    crsr.execute('create table ComponentNames(ExpID, ComponentID, Name, PRIMARY KEY(ExpID, ComponentID, Name))')

    #Plates
    crsr.execute('create table Plates(FactoryName UNIQUE, Rows, Columns)')
    crsr.execute('create table PlateLocations(ExpID, Plate, FactoryName, Grid, Site, PRIMARY KEY(ExpID, Plate))')
    crsr.execute('create table PlateNicknames(ExpID, Plate, Nickname, PRIMARY KEY(ExpID, Nickname))')

    #Volumes
    crsr.execute('create table Volumes(ExpID, VolumeName, VolumeValue, PRIMARY KEY(ExpID, VolumeName))')

    #Recipes
    crsr.execute('create table Recipes(ExpID, Recipe, Row, Column, Name, Volume, PRIMARY KEY(ExpID, Recipe, Row, Column))')
    crsr.execute('create table Subrecipes(ExpID, Recipe, Row, Subrecipe, PRIMARY KEY(ExpID, Recipe, Row, Subrecipe))')

    #Transactions
    crsr.execute('create table Actions(ExpID, ActionID, Type, PRIMARY KEY(ExpID, ActionID));')
    crsr.execute('create table Transfers(ExpID, ActionID, trOrder, srcWellID, dstWellID, Volume, Method, PRIMARY KEY(ExpID, ActionID, trOrder, srcWellID, dstWellID));')
    crsr.execute('create table Commands(ExpID, ActionID, trOrder, Command, Options, PRIMARY KEY(ExpID, ActionID, trOrder));')
    crsr.execute('create table CommandLocations(ExpID, ActionID, trOrder, Location, PRIMARY KEY(ExpID, ActionID, Location));')

    #Updating experiments
    crsr.execute('insert into Experiments values(0, "", "", "");')

    DatabaseDisconnect()

def UpdateMethods():
    methodFile = open('methodsInfo.txt', 'r')
    f = methodFile.readlines()

    for method in f:
        try:
            DatabaseConnect()
            if f.index(method) == 0:
                message = 'INSERT INTO DefaultMethod VALUES("' + str(method.strip()) + '");'
            else:
                message = 'INSERT INTO Methods VALUES("' + str(method.strip()) + '");'
            crsr.execute(message)
            DatabaseDisconnect()
        except sqlite3.IntegrityError:
            pass

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
            message = 'INSERT INTO Plates VALUES("' + name + '",' + size[0] + ',' + size[1] + ');'
            DatabaseConnect()
            crsr.execute(message)
        except sqlite3.IntegrityError:
            DatabaseConnect()
            crsr.execute(message)
            message = 'UPDATE Plates SET Rows = ' + size[0] + ', Columns = ' + size[1] + '  WHERE FactoryName = ' + '"' + name + '"'
        DatabaseDisconnect()

def CreateFolders():
    dirs = ['esc', 'incoming', 'logs']
    for directory in dirs:
        if not os.path.exists(directory):
            os.mkdir(directory)
            os.chmod(directory, stat.S_IRWXU|stat.S_IRWXG|stat.S_IRWXO)

def setup():
    CreateFolders()
    CreateTables()
    UpdatePlates()
    UpdateMethods()
    os.chmod('prpr.db', stat.S_IRWXU|stat.S_IRWXG|stat.S_IRWXO)
    print('Done!')

if __name__ == '__main__':
    setup()
