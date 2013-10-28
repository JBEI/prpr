__author__ = 'Nina Stawski'
__version__ = '0.32'

def CheckCommand(command):
    """
    Returns the command type and the generic command, if the command exists.
    """
    commandList = {
        'definition' : {
            'name'          : ['NAME'],
            'table'         : ['TABLE'],
            '"""'           : ['"""', '"""""', '""""""', '"""""""', '""""""""','DOC', 'ENDDOC'],
            'plate'         : ['PLATE'],
            'component'     : ['COMPONENT', 'REAGENT', 'LOCATION'],
            'volume'        : ['VOLUME', 'AMOUNT'],
            'recipe'        : ['RECIPE', 'LIST', 'SET'],
            'comment'       : ['COMMENT', '%']
        },
        'action' : {
            'use'           : ['USE'],
            'make'          : ['MAKE', 'PREPARE_LIST'],
            'spread'        : ['SPREAD', 'DISTRIBUTE', 'DIST_REAGENT'],
            'transfer'      : ['TRANSFER', 'TRANSFER_LOCATIONS'],
            'message'       : ['MESSAGE', 'PROMPT'],
            'move'          : ['MOVE'],
            'wait'          : ['WAIT']
        },
        'function' : {
            'protocol'      : ['TEMPLATE', 'PROTOCOL'],
            'endprotocol'   : ['ENDTEMPLATE', 'ENDPROTOCOL']
        }
    }

    for type in commandList.keys():
        for keyword in commandList[type].keys():
            if command.upper() in commandList[type][keyword]:
                return { 'type' : type, 'name' : keyword }