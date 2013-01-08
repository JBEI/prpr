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
        if ((src != 'undefined') && (dst != 'undefined')) {
            if (wells[source]) {
                wells[source].push(dst);
            }
            else {
                wells[source] = [dst];
            }
            ;
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

function addMFInfo() {
    if ($('#devices').val() == 'microfluidics') {
        var position = getPositionString();
        $('#position').val(position);
        saveConnections();
    }
    ;
};

function saveConnections() {
    var wells = getConnectionInfos();
    $('#wells').val(wells);
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
    $('#mfdata').after('<button class="btn btn-info pull-right" id="loadButton"  data-toggle="modal" href="#myModal" onClick="loadMFTable();">View/Edit the plate</button>');
//    loadMFTable();
};

function setupDroppableWells() {
    var grid = [45, 45];
    $('#wellSrc').draggable({
        helper:"clone",
        grid:grid
    });
    $('#field').droppable({
        accept:"#wellSrc",
        drop:function (event, ui) {
            var counter = $('.mf-well').length;
            var clone = $('#wellSrc').clone(false);
            var top = ui.helper.position()['top'];
            var left = ui.helper.position()['left'];
            var id = 'id' + counter;
            clone.attr({ 'id':id, 'name':id }).css({'top':top, 'left':left, 'position':'absolute'}).addClass('mf-well').appendTo('#field');
            makeDraggable(id);
            addEndpoint(id);
            addMFInfo();
        }
    });
};

function resetMFField() {
    jsPlumb.deleteEveryEndpoint();
    jsPlumb.reset();
    $('#mffile').remove();
    $('#platename').html('Microfluidics plate');
    $('#tablerow').html('<div id="field" class="wells">' +
        '<div id="source">' +
        '<div id="wellSrc" class="prpr-well x4x6 mf"></div>' +
        '</div>' +
        '</div>');
    $('#button-close-modal').after('<form id="mffile" class="pull-right">' +
        '<div onclick="getMFTableFile();" class="btn btn-link">Download table file</div>' +
        '</form>');
    setupDroppableWells();
};

function loadMFTable() {
    resetMFField();
    $('.modal-body').css('max-height', '900px');
    var file = $('#mfdata')[0].files[0];
    var formData = new FormData();
    formData.append("file", file);
    $.ajax({
        url:'mfparse',
        type:'POST',
        data:formData,
        cache:false,
        contentType:false,
        processData:false,
        success:function (data) {
            //ParseMFData(data);
            var mfplate = JSON.parse(data);
            var views = mfplate[0];
            var connections = mfplate.slice(1);
            $('#position').val(views);
            $('#wells').val(connections);
            parseViews(views);
            parseConnections(connections);
            $('#loadButton').attr('onClick', '');
            addMFInfo();
        }
    });
};

function addEndpoint(element) {
    var name = $('#' + element).attr('name');
    $('#' + element).append('<div class="mf-label" onClick="renameWell(' + "'" + element + "'" + ');">' + name + '<i class="icon-pencil icon-white"></i></div>');
    jsPlumb.addEndpoint('' + element + '', {
            anchor:[
                [0.5, 0.5, 0, -1],
                "Center"
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
        $('#' + id).css({'top':top + 'px', 'left':left + 'px', 'position':'absolute'});
        addEndpoint(id);
        makeDraggable(id);
//        jsPlumb.draggable(id, {grid:grid});
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
    jsPlumb.repaintEverything();
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