__author__ = 'Nina Stawski'
__version__ = '0.3'

def CheckCommand(command):
    """
    Returns the command type and the generic command, if the command exists.
    """
    commandList = {
        'definition' : {
            'name'          : ['NAME'],
            'table'         : ['TABLE'],
            '"""'           : ['"""', '""""""','DOC', 'ENDDOC'],
            'plate'         : ['PLATE'],
            'component'     : ['COMPONENT', 'REAGENT'],
            'volume'        : ['VOLUME', 'AMOUNT'],
            'recipe'        : ['RECIPE', 'LIST', 'SET'],
            'comment'       : ['COMMENT', '%']
        },
        'action' : {
            'make'          : ['MAKE', 'PREPARE_LIST'],
            'spread'        : ['SPREAD', 'DISTRIBUTE', 'DIST_REAGENT'],
            'transfer'      : ['TRANSFER', 'TRANSFER_LOCATIONS'],
            'message'       : ['MESSAGE', 'PROMPT']
        }
    }

    for type in commandList.keys():
        for keyword in commandList[type].keys():
            if command.upper() in commandList[type][keyword]:
                return { 'type' : type, 'name' : keyword }