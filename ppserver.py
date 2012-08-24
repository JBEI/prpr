__author__ = 'Nina Stawski'
__version__ = '0.2'

import bottle
from bottle import *
import os
from parpar import *
from parparser import *
from tempfile import TemporaryFile


global robotTips
global maxAm
robotTips = 8
maxAm = 150

@route('/')
def parpar():
    return template('pages' + os.sep + 'page.html', file = '', btn = '', text = '', hide = 'hide',  codeerror = 'hide', fileerror = 'hide', alertsuccess = 'hide', tables = GetDefaultTables(), version = __version__)

@post('/table')
def table():
    plateIndexes = {}
    plateNicknames = {}
    tablename = request.body.read().decode()
    tabledirname = 'tables' + os.sep
    plateFile = open(tabledirname + tablename, "r")
    PlateFileParse(plateFile, plateIndexes, plateNicknames)
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
    PlateFileParse(plateFile, plateIndexes, plateNicknames) #plateFile
    plates = []
    for key in plateIndexes.keys():
        plates.append([key, [plateIndexes[key][0], plateIndexes[key][1]], plateNicknames[key]])
        tojs = json_dumps(plates)
    return tojs

@post('/sample')
def sample():
    config = open('parpar_sample.par', 'r')
    return config.readlines()

@post('/getconfig')
def config():
    getconfig = request.forms.get('text', '').strip()
    preselected = request.forms.get('tableselect')
    data = request.files.data
    print('filelength', len(request.files))
    if getconfig != '':
        DatabaseConnect()
        global expID
        expID = str(int(ExecuteCommand('SELECT max(ExpID) FROM Experiments;')[0]) + 1)

        if data != '':
            raw = data.file.read()
            tablename = 'tables_' + expID + '.ewt'
            tabledirname = 'tables' + os.sep
            tablefile = open(tabledirname + tablename, "wb")
#            except IOError:
#                os.mkdir(tabledirname)
#                tablefile = open(tabledirname + tablename, "wb")
            tablefile.write(raw)
            tablefile.close()
        else:
            if preselected != 'select':
                tablename = preselected
            else:
                return template('pages' + os.sep + 'page.html', file = '', btn = '', text = getconfig, hide = 'hide', fileerror = '', codeerror = 'hide', alertsuccess = 'hide', tables = GetDefaultTables(), version = __version__)
        dirname = 'incoming' + os.sep
        filename = 'config_' + expID + '.par'
        writefile = open(dirname + filename, "w")
#        except IOError:
#            os.mkdir(dirname)
#            writefile = open(dirname + filename, "w")
        if getconfig.startswith('TABLE'):
            getconfig = '\n'.join(getconfig.split('\n')[1:]) #removing the extra 'TABLE' from the config file
        list = ['TABLE ', tablename ,'\n', '\n', getconfig] #adding the chosen/uploaded table to the config file
        writefile.writelines( ''.join(list) )
        writefile.close()
        readfile = open(dirname + filename, "r")
        testindex = ParseFile(readfile, expID)
        print(testindex)
        if testindex > 0:
            LiquidTransfer(expID, robotTips)
            wash = Wash()
            AppendToRobotCfg(expID, wash)
            file = 'config' + str(expID) + '.esc'
            return template('pages' + os.sep + 'page.html', file = file, btn = 'btn-success', text = getconfig, hide = '', codeerror = 'hide', fileerror = 'hide', alertsuccess = '', tables = GetDefaultTables(), version = __version__)
        else:
            return template('pages' + os.sep + 'page.html', file = '', btn = '', text = '', hide = 'hide', codeerror = '', fileerror = 'hide', alertsuccess = 'hide', tables = GetDefaultTables(), version = __version__)
    else:
        return template('pages' + os.sep + 'page.html', file = '', btn = '', text = '', hide = 'hide', codeerror = '', fileerror = 'hide', alertsuccess = 'hide', tables = GetDefaultTables(), version = __version__)
#    elif getconfig != '' and data == '':

@route('/static/:path#.+#', name='static')
def static(path):
    return static_file(path, root='static')

@route('/download/<filename>')
def download(filename):
    print(filename)
    return static_file(filename, root='esc', download=filename)

@route('/get/<filename>')
def download(filename):
    print(filename)
    return static_file(filename, root='tables', download=filename)

def GetDefaultTables():
    DatabaseConnect()
    tablesDir = os.listdir('tables')
    tables = []
    for name in tablesDir:
        if 'JBEI' in name:
            tables.append(name)
        if 'BreakfastDrinks' in name:
            tables.append(name)
    tables.sort()
    jsonTables = json_dumps(tables)
    DatabaseDisconnect()
    return jsonTables

if __name__ == '__main__':
    bottle.debug(True)
    run(host='localhost', port=8080, reloader=True)
