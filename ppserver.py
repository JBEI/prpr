#!/usr/bin/env python3
__author__ = 'Nina Stawski'
__version__ = '0.3'

import bottle
from bottle import *
import os
#from parpar import *
from parparser import *
from tempfile import TemporaryFile


global robotTips
global maxAm
robotTips = 8
maxAm = 150

@route('/')
def parpar():
    return template('pages' + os.sep + 'page.html', file='', btn='', text='', alerterror=[], alertsuccess=[], tables=GetDefaultTables(), version=__version__)

@route('/preview')
def preview():
    return template('pages' + os.sep + 'page_dev.html', version=__version__)

@route('/disclaimer')
def disclaimer():
    return template('pages' + os.sep + 'disclaimer.html', version=__version__)
    
@route('/copyright')
def copyright():
    return template('pages' + os.sep + 'copyright.html', version=__version__)

@post('/table')
def table():
    plateIndexes = {}
    plateNicknames = {}
    experiment=False
    tablename = request.body.read().decode()
    tabledirname = 'default_tables' + os.sep
    plateFile = open(tabledirname + tablename, "r")
    PlateFileParse(plateFile, experiment, plateNicknames, plateIndexes)
    print(plateNicknames, plateIndexes)
    plates = []
    for key in plateIndexes.keys():
        plates.append([key, [plateIndexes[key][0], plateIndexes[key][1]], plateNicknames[key]])
        tojs = json_dumps(plates)
    return tojs

@post('/plates')
def plates():
    a = request.body.read().decode().split('\n')[2:-2]
    plateFile = TemporaryFile(mode='r+')
    plateFile.writelines(a)
    plateFile.seek(0)
    plateIndexes = {}
    plateNicknames = {}
    experiment = False
    PlateFileParse(plateFile, experiment, plateNicknames, plateIndexes)
    plates = []
    for key in plateIndexes.keys():
        plates.append([key, [plateIndexes[key][0], plateIndexes[key][1]], plateNicknames[key]])
        tojs = json_dumps(plates)
    print(plateNicknames, plateIndexes)
    return tojs

@post('/sample')
def sample():
    config = open('parpar_sample.par', 'r')
    return config.readlines()

@post('/getconfig')
def config():
    errorList = []
    successList = []
    getconfig = request.forms.get('text', '').strip()
    preselected = request.forms.get('tableselect')
    customMethods = request.forms.get('methods', '').strip().split(',')
    data = request.files.data
    if getconfig != '':
        db=DBHandler()
        global experiment
        if customMethods != ['']:
            experiment = Experiment(maxVolume=150,tips=8,db=db,userMethods=customMethods)
        else:
            experiment = Experiment(maxVolume=150,tips=8,db=db)
        expID = experiment.ID


        if data != '':
            raw = data.file.read()
            tablename = 'tables' + os.sep + 'tables_' + expID + '.ewt'
            tablefile = open(tablename, "wb")
            tablefile.write(raw)
            tablefile.close()
        else:
            if preselected != 'select':
                tablename = 'default_tables' + os.sep + preselected
            else:
                errorList.append("Please select or upload the table file for your configuration script.")
                return template('pages' + os.sep + 'page.html', file = '', btn = '', text = getconfig, alerterror = errorList, alertsuccess = successList, tables = GetDefaultTables(), version = __version__)

        dirname = 'incoming' + os.sep
        filename = 'config_' + expID + '.par'
        writefile = open(dirname + filename, "w")
        if getconfig.startswith('TABLE'):
            getconfig = '\n'.join(getconfig.split('\n')[1:]) #removing the extra 'TABLE' from the config file
        list = ['TABLE ', tablename, '\n', '\n', getconfig] #adding the chosen/uploaded table to the config file.
        writefile.writelines( ''.join(list) )
        writefile.close()
        readfile = open(dirname + filename, "r")
        ParseFile(readfile, experiment)

        if len(experiment.errorLogger):
            for item in experiment.errorLogger:
                errorList.append(item)
            return template('pages' + os.sep + 'page.html', file = '', btn = 'btn-success', text = getconfig, alerterror = errorList, alertsuccess = successList, tables = GetDefaultTables(), version = __version__)

        elif experiment.testindex:
            parpar = ParPar(expID)
            file = 'config' + str(expID) + '.esc'
            log = 'experiment' + str(expID) + '.log'
            successList.append("Your configuration file has been successfully processed.")
            return template('pages' + os.sep + 'page.html', file = file, btn = 'btn-success', text = getconfig, alerterror = errorList, alertsuccess = successList, tables = GetDefaultTables(), version = __version__)

        else:
            errorList.append("Your configuration file doesn't contain any actions. Please refer to PaR-PaR howto guide.")
            return template('pages' + os.sep + 'page.html', file = '', btn = 'btn-success', text = getconfig, alerterror = errorList, alertsuccess = successList, tables = GetDefaultTables(), version = __version__)

    else:
        errorList.append("Your configuration file doesn't contain any actions. Please refer to PaR-PaR howto guide.")
        return template('pages' + os.sep + 'page.html', file = '', btn = 'btn-success', text = getconfig, alerterror = errorList, alertsuccess = successList, tables = GetDefaultTables(), version = __version__)

@route('/static/:path#.+#', name='static')
def static(path):
    return static_file(path, root='static')

@route('/download/<filename>')
def download(filename):
    print(filename)
    if filename.startswith('config'):
        root = 'esc'
    else:
        root = 'logs'
    return static_file(filename, root, download=filename)

@route('/get/<filename>')
def download(filename):
    print(filename)
    return static_file(filename, root='tables', download=filename)

def GetDefaultTables():
    """
    Getting a list of default tables from folder 'tables'
    """
    tablesDir = os.listdir('default_tables')
    tables = []
    for name in tablesDir:
        if not name.startswith('.'):
            tables.append(name)
    tables.sort()
    jsonTables = json_dumps(tables)
    return jsonTables

if __name__ == '__main__':
    bottle.debug(True)
    run(host='localhost', port=8080, reloader=True)
