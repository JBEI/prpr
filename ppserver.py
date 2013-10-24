#!/usr/bin/env python3

# ppserver.py, a part of PR-PR (previously known as PaR-PaR), a biology-friendly language for liquid-handling robots
# Author: Nina Stawski, nstawski@lbl.gov, me@ninastawski.com
# Copyright 2012-2013, Lawrence Berkeley National Laboratory
# http://github.com/JBEI/prpr/blob/master/license.txt

__author__ = 'Nina Stawski'
__version__ = '1.1'

import bottle
from bottle import *
import os
from prparser import *
from tempfile import TemporaryFile
import glob
import importlib
from prpr_microfluidics import *
from prpr_tecan import *

global robotTips
global maxAm
robotTips = 8
maxAm = 150

@route('/')
def prpr():
    return template('pages' + os.sep + 'page.html', file='', btn='', text='', alerterror=[], alertsuccess=[], tables=GetDefaultTables(), selected='tecan', version=__version__)

@post('/preview')
def preview():
    a = {'response' : 'error', 'config' : ['1', '2'], 'somethingelse' : {'somethign' : 'else'}}
    return json_dumps(a)


@route('/dev')
def dev():
    return template('pages' + os.sep + 'page_dev.html', version=__version__)


@route('/mf')
def mf():
    return template('pages' + os.sep + 'dev-mf.html', version=__version__)


@route('/disclaimer')
def disclaimer():
    return template('pages' + os.sep + 'disclaimer.html', version=__version__)

@route('/copyright')
def copyright_():
    return template('pages' + os.sep + 'copyright.html', version=__version__)


@post('/table')
def table():
    plateIndexes = {}
    plateNicknames = {}
    experiment = False
    tablename = request.body.read().decode()
    tabledirname = 'default_tables' + os.sep
    plateFile = open(tabledirname + tablename, "r")
    PlateFileParse(plateFile, experiment, plateNicknames, plateIndexes)
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
    return tojs


@post('/mfplates')
def mfplates():
    position = request.forms.get('position', '')
    wells = request.forms.get('wells', '')
    mywells = '\n'.join(json_loads(wells))
    tablename = createMFPlate(mywells, position)
    return tablename


def createMFPlate(wells, position):
    directory = 'tables'
    mydata = position + '\n' + wells
    fileCounter = len(glob.glob1(directory, "tables_mf_*"))
    tablename = 'tables_mf_' + str(fileCounter) + '.mfp'
    tablefile = open(directory + os.sep + tablename, "wb")
    tablefile.write(bytes(mydata, 'UTF-8'))
    tablefile.close()
    return tablename


@post('/mfparse')
def mfparse():
    info = request.body.read().decode()
    if info[-3:] == 'mfp':
        tabledirname = 'default_tables' + os.sep
        with open(tabledirname + info, "r") as plateFile:
            a = plateFile.readlines()
    else:
        a = request.body.read().decode().split('\n')[4:-2]
        a[-1] = a[-1].strip()
    tojs = json_dumps(a)
    return tojs


@post('/sample')
def sample():
    platform = request.body.read().decode()
    configFile = 'prpr_sample_' + platform + '.par'
    config = open('samples/' + configFile, 'r')
    return config.readlines()

@post('/getMethods')
def getMethods():
    db = DBHandler()
    methods = db.getMethods()
    return json_dumps(methods)

@post('/getPlates')
def getPlates():
    db = DBHandler()
    plates = db.getPlates()
    return json_dumps(plates)


@post('/getconfig')
def config():
    errorList = []
    successList = []
    platform = request.forms.get('deviceselect', '').strip()
    getconfig = request.forms.get('text', '').strip()
    customMethods = request.forms.get('methods', '').strip().split(',')
    if getconfig != '':
        db = DBHandler()
        global experiment
        if customMethods != ['']:
            experiment = Experiment(maxVolume=150, tips=8, db=db, platform=platform, userMethods=customMethods)
        else:
            experiment = Experiment(maxVolume=150, tips=8, platform=platform, db=db)
        expID = experiment.ID
        
        print('platform:', platform)

        if platform == 'tecan':
            preselected = request.forms.get('tableselect')
            data = request.files.data
            if data != '':
                fileExtension = data.filename[-3:]
                raw = data.file.read()
                tablename = 'tables' + os.sep + 'tables_' + expID + '.' + fileExtension
                tablefile = open(tablename, "wb")
                tablefile.write(raw)
                tablefile.close()
            else:
                if preselected != 'select':
                    tablename = 'default_tables' + os.sep + preselected
                else:
                    errorList.append("Please select or upload the table file for your configuration script.")
                    return template('pages' + os.sep + 'page.html', file='', btn='', text=getconfig, alerterror=errorList, alertsuccess=successList,tables=GetDefaultTables(), selected=platform, version=__version__)
        elif platform == 'microfluidics':
            preselected = request.forms.get('mftableselect')
            #note: if the platform is microfluidics
            if preselected != 'select':
                tablename = 'default_tables' + os.sep + preselected
            else:
                position = request.forms.get('position', '')
                wells = '\n'.join(request.forms.get('wells', '').strip().split(';'))
                tablename = 'tables' + os.sep + createMFPlate(wells, position)

        dirname = 'incoming' + os.sep
        filename = 'config_' + expID + '.par'
        writefile = open(dirname + filename, "w")

        if getconfig.startswith('TABLE'):
            getconfig = '\n'.join(getconfig.split('\n')[1:]) #removing the extra 'TABLE' from the config file
        if (platform != 'human') and (platform != 'microscope'):
            list_ = ['TABLE ', tablename, '\n', '\n', getconfig] #adding the chosen/uploaded table to the config file.
        else:
            list_ = getconfig
        writefile.writelines(''.join(list_))
        writefile.close()
        readfile = open(dirname + filename, "r")
        platform = __import__('prpr_'+ experiment.platform)
        ParseFile(readfile, experiment)

        if len(experiment.errorLogger):
            for item in experiment.errorLogger:
                errorList.append(item)
            return template('pages' + os.sep + 'page.html', file='', btn='btn-success', text=getconfig, alerterror=errorList, alertsuccess=successList, tables=GetDefaultTables(), selected=platform, version=__version__)

        elif experiment.testindex:
            if experiment.platform == 'human':
                platformFileExtension = 'txt'
            elif experiment.platform == 'microscope':
                platformFileExtension = 'py'
            else:
                platformFileExtension = platform.defaults.fileExtensions[tablename[-3:]]
            file = 'config' + str(expID) + '.' + platformFileExtension
            prpr = platform.PRPR(experiment.ID)
            log = 'experiment' + str(expID) + '.log'
            successList.append("Your configuration file has been successfully processed.")

            return template('pages' + os.sep + 'page.html', file=file, btn='btn-success', text=getconfig, alerterror=errorList, alertsuccess=successList, tables=GetDefaultTables(), selected=platform, version=__version__)

        else:
            errorList.append("Your configuration file doesn't contain any actions. Please refer to PR-PR howto guide.")
            return template('pages' + os.sep + 'page.html', file='', btn='btn-success', text=getconfig, alerterror=errorList, alertsuccess=successList, tables=GetDefaultTables(), selected=platform, version=__version__)

    else:
        errorList.append("Your configuration file doesn't contain any actions. Please refer to PR-PR howto guide.")
        return template('pages' + os.sep + 'page.html', file='', btn='btn-success', text=getconfig, alerterror=errorList, alertsuccess=successList, tables=GetDefaultTables(), selected=platform, version=__version__)


@route('/static/:path#.+#', name='static')
def static(path):
    return static_file(path, root='static')


@route('/download/<filename>')
def download(filename):
    if filename.startswith('config'):
        root = 'esc'
    elif filename.startswith('tables_mf_'):
        root = 'tables'
    else:
        root = 'logs'
    return static_file(filename, root, download=filename)


@route('/get/<filename>')
def download(filename):
    return static_file(filename, root='tables', download=filename)


def GetDefaultTables():
    """
    Getting a list of default tables from folder 'tables'
    """
    tablesDir = os.listdir('default_tables')
    tables = []
    for name in tablesDir:
        if not name.startswith('.') and (name.endswith('.ewt') or name.endswith('.gem') or name.endswith('.mfp')):
            tables.append(name)
    tables.sort()
    jsonTables = json_dumps(tables)
    return jsonTables

if __name__ == '__main__':
    bottle.debug(True)
    run(host='localhost', port=8080, reloader=True)