/**
 * Author: Nina Stawski, me@ninastawski.com
 * Date: 12/18/12
 * Time: 10:33 AM
 */

function getConnectionInfos() {
    var wells = [];
    var connections = jsPlumb.getConnections();
    for (i = 0; i < connections.length; i++) {
        var connection = connections[i];
        var src = $('#' + connection.sourceId).attr('name');
        var dst = $('#' + connection.targetId).attr('name');
        var source = src;
        //if (renamed.match(src)) {
        //var source = renamed[src];
        //}
        //else {
        //var source = src;
        //};
        if (wells[source]) {
            wells[source].push(dst);
        }
        else {
            wells[source] = [dst];
        }
        ;
    }
    var cns = [];
    for (var i = 0; i < Object.keys(wells).length; i++) {
        var well = Object.keys(wells)[i];
        if (wells[well]) {
            var wellinfo = well + ':';
            for (var k = 0; k < wells[well].length; k++) {
                var conn = wells[well][k];
                wellinfo += conn;
                if (k != wells[well].length - 1) {
                    wellinfo += ',';
                }
            }
            cns.push(wellinfo);
        }
    }
    ;
    return cns;
};

function getPositionString() {
    var position = '';
    $('.mf-well').each(function () {
        var id = this.id;
        var name = $('#' + id).attr('name');
        var top = $('#' + id).position()['top'];
        var left = $('#' + id).position()['left'];
        position += (name + ':' + top + ',' + left + ';');
    });
    return position;
};

function getMFTableFile() {
    var position = getPositionString();
    var wells = getConnectionInfos();
    var formData = new FormData();
    formData.append("position", position);
    formData.append("wells", JSON.stringify(wells));
    $.ajax({
        url:'mfplates',
        type:'POST',
        data:formData,
        cache:false,
        contentType:false,
        processData:false,
        success:function (data) {
            $('#mffile').attr('action', '/download/' + data).submit();
        }
    });
};
function mfAppendLoadButton() {
    $('#loadButton').remove();
    $('#mfdata').after('<div class="btn" id="loadButton" onClick="loadMFTable()">Load the plate</div>');
};
function loadMFTable() {
    var file = $('#mfdata')[0].files[0];
    var formData = new FormData();
    formData.append("file", file);
    $('#field').children().remove();
    $.ajax({
        url:'mfparse',
        type:'POST',
        data:formData,
        cache:false,
        contentType:false,
        processData:false,
        success:function (data) {
            //ParseMFData(data);
            jsPlumb.reset();
            var mfplate = JSON.parse(data);
            var views = mfplate[0];
            parseViews(views);
            jsPlumb.repaintEverything();
            var connections = mfplate.slice(1);
            parseConnections(connections);
        }
    });
};
function addEndpoint(element) {
    var name = $('#' + element).attr('name');
    $('#' + element).append('<div class="mf-label" onClick="renameWell(' + "'" + element + "'" + ');">' + name + '<i class="icon-pencil icon-white"></i></div>');
    jsPlumb.addEndpoint('' + element + '', {
            anchor:[
                [0.5, 0.5, 0, -1],
                "Continuous"
            ],
            maxConnections:20,
            connector:"Straight" //-["StateMachine", {curviness:0}]
        },
        {
            isSource:true,
            isTarget:true
        });
};

function makeDraggable(element) {
    $('#' + element).draggable({
        drag:function (event, ui) {
            jsPlumb.repaintEverything();
        },
        stop:function (event, ui) {
            jsPlumb.repaintEverything();
        },
        grid:grid
    });
};
function parseViews(string) {
    var views = string.split(';').slice(0, -1);
    for (var i = 0; i < views.length; i++) {
        var element = views[i].split(':');
        var id = element[0];
        var coords = element[1].split(',');
        var top = coords[0];
        var left = coords[1];
        $('#field').append('<div class="mf-well prpr-well x4x6 mf" id="' + id + '" name="' + id + '" style=""></div>');
        addEndpoint(id);
        makeDraggable(id);
        $('#' + id).css({'top':top + 'px', 'left':left + 'px', 'position':'absolute'});
    }
    ;
};

function parseConnections(list) {
    for (var i = 0; i < list.length; i++) {
        var element = list[i].split(':');
        var source = jsPlumb.getEndpoints(element[0]);
        if (source) {
            var src = source[0];
            var dstList = element[1].split(',');
            for (var j = 0; j < dstList.length; j++) {
                var dst = jsPlumb.getEndpoints(dstList[j])[0];
                jsPlumb.connect({source:src, target:dst});
            }
            ;
        }
        ;
    }
    ;
};

function renameWell(elementID) {
    var name = $('#' + elementID).attr('name');
    $('#' + elementID).children('.mf-label').remove();
    $('#' + elementID).append('<input type="text" class="input-mf" value="' + name + '" onBlur="applyIDChanges(' + "'" + elementID + "'" + ')"></input>');
};

function applyIDChanges(id) {
    var newName = $('#' + id).children().eq(0).val();
    $('#' + id).attr('name', newName);
    $('#' + id).children('.input-mf').remove();
    $('#' + id).append('<div class="mf-label" onClick="renameWell(' + "'" + id + "'" + ');">' + newName + '<i class="icon-pencil icon-white"></i></div>');
};