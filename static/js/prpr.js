/**
 * prpr.js, a part of PR-PR (previously known as PaR-PaR), a biology-friendly language for liquid-handling robots
 * Author: Nina Stawski, nstawski@lbl.gov, me@ninastawski.com
 * Copyright 2012, Lawrence Berkeley National Laboratory
 * http://github.com/JBEI/prpr/blob/master/license.txt
 */

function selectDevice(selection) {
    $('.alert').remove();
    $('#prpr-platform').children().removeClass('btn-info');
    $('#platform-' + selection).addClass('btn-info');
    console.log(selection);
    console.log( $('#platform-' + selection));
//    var selection = $('#device').find('option:selected').val();
    if (selection == 'freedomevo') {
        $('#deviceselect').val('freedomevo');
        $('#microfluidics').addClass('hidden');
        $('#tablefile h4').html('Select/upload table file');
        $('#tablefile .controls').attr('id', 'table');
        $('#tablefile .controls select').attr({ 'id' : 'tables', 'name' : 'tableselect', 'onchange' : 'selectClicked(\'table\');' });
        $('#tablefile .controls input').attr({'id' : 'data', 'name' : 'data', 'onchange' : 'AppendUploadButton()' });
        setTimeout(function() {
            if ($('#data').val()) {
                $('#uploadFile').remove();
                $('#loadButton').remove();
                AppendUploadButton()
            }
        }, 0);
        $('#methodsToggle').removeClass('hidden');
        $('#sampleScript').removeClass('hidden');
    }
    else if (selection == 'microfluidics') {
        $('#deviceselect').val('microfluidics');
        $('#microfluidics').removeClass('hidden');
        $('#tablefile h4').html('Upload microfluidics table');
        $('#tablefile .controls').attr('id', 'mftable');
        $('#tablefile .controls select').attr({ 'id' : 'mftables', 'name' : 'mftableselect', 'onchange' : 'selectClicked(\'mftable\');' });
        $('#tablefile .controls input').attr({'id' : 'mfdata', 'name' : 'mfdata', 'onchange' : 'loadMFTable(\'loadButtonOnClick\');mfAppendLoadButton()' });
        setTimeout(function() {
            if ($('#mfdata').val()) {
                console.log('mfdata val!!!');
                $('#uploadFile').remove();
                loadMFTable('loadButtonOnClick');
                $('#mfdata').after('<button class="btn btn-info pull-right" id="loadButton"  data-toggle="modal" href="#myModal" onClick="loadMFTable();">View/Edit the plate</button>');
            }
        }, 0);
        $('#mftables').children().remove();
        $('#mftables').prepend('<option value="select">Upload table file</option><option value="mfcreatenew">Create new</option>');
        $('#methodsToggle').addClass('hidden');
        $('#loadButton').remove();
        $('#methods').addClass('hide');
        $('#result').before('<div class="alert"><i class="icon-exclamation-sign large"></i>&nbsp;<strong>Warning:</strong> Microfluidics functionality may not work correctly in <strong>Internet Explorer</strong>. Please use <strong>Chrome</strong> or <strong>Firefox</strong>.</div>');
        resetMFField();
        $('#sampleScript').addClass('hidden');
    }
}

function createTablesList(tablesList) {
    $('#tables').children().remove();
    $('#tables').prepend('<option value="select">Select table file</option>');
    for (var i = 0; i < tablesList.length; i++) {
        var tableName = tablesList[i];
        var tableSelector;
        if (tableName.substr(-4, 4) == '.ewt') {
            tableSelector = 'tables';
            $('#' + tableSelector).append('<option value="' + tableName + '">' + tableName + '</option>')
        } //else if (tableName.substr(-4, 4) == '.mfp') {
        //tableSelector = 'mftables';
        //}
    }
}

function selectClicked(selectID) {
    var selection = $('#' + selectID).find('option:selected').val();
    var preview, filename, changeFunction, clickFunction;
    if (selectID == 'table') {
        preview = 'preview'
        filename = 'data'
        changeFunction = 'AppendUploadButton();'
        clickFunction = 'CallPython();'
    }
    else if (selectID == 'mftable') {
        preview = 'mfpreview'
        filename = 'mfdata'
        changeFunction = 'mfAppendLoadButton();'
        clickFunction = 'loadMFTable();'
        resetMFField();
    }

    if (selection == 'select') {
        $('#' + preview).remove();
        $('#' + selectID).append('<input type="file" name="' + filename + '" id="' + filename + '" class="span3" onchange="loadMFTable();' + changeFunction + '"/>');
    }
    else if (selection == 'mfcreatenew') {
        $('#' + filename).remove();
        $('#' + preview).remove();
        $('#loadButton').remove();
        $('#' + selectID).append('<button id="' + preview + '" class="btn btn-info pull-right" data-toggle="modal" href="#myModal">Edit table layout</button>');
        resetMFField();
        $('#myModal').modal('show');
        setupDroppableWells(0);
    }
    else {
        console.log(selectID, selection);
        $('#' + filename).remove();
        $('#' + preview).remove();
        $('#loadButton').remove();
        $('#' + selectID).append('<button id="' + preview + '" class="btn btn-info pull-right" data-toggle="modal" href="#myModal" onclick="' + clickFunction + '">Preview table layout</button>');
    }
}

function AppendUploadButton() {
    $('#uploadFile').remove();
    $('#table').append('<button id="uploadFile" class="btn btn-info pull-right"  data-toggle="modal" href="#myModal" onclick="UploadTable();">Preview table layout</button>');
}

function LoadSampleScript() {
    $('.alert').remove();
    $('#data').remove();
    $('#preview').remove();
    $('#uploadFile').remove();
    $('#table').append('<button id="preview" class="btn btn-info pull-right" data-toggle="modal" href="#myModal" onclick="CallPython();">Preview table layout</button>');
    $('#tables').val('BreakfastDrinks.ewt');
    $.post('sample', function (data) {
        $('#textarea').val(data);
    });
}

function UploadTable() {
    var file = $('#data')[0].files[0];
    var formData = new FormData();
    formData.append("file", file);
    $('#tablerow').children().remove();
    $.ajax({
        url:'plates',
        type:'POST',
        data:formData,
        cache:false,
        contentType:false,
        processData:false,
        success:function (data) {
            $('#platename').html(file.name);
            ParseTableData(data);
        }
    });
}

function CallPython() {
    var data = $('#tables').find('option:selected').val();
    $('#tablerow').children().remove();
    $('#mffile').remove();
    $.post('table', data, function (data) {
        $('#platename').html($('#tables').find('option:selected').val());
        ParseTableData(data);
    });
}

function ParseTableData(data) {
    for (var j = 1; j <= 3; j++) {
        $('#tablerow').append('<div id="row' + j + '"></div>');

        for (var i = 1; i <= 30; i++) {
            $('#row' + j).append('<div class="prpr-grid grid-empty" id="' + i + '"></div>');
        }
        $('#row' + j).children('#1').removeClass('grid-empty').addClass('grid-system').append('<div class="rotate">system</div>').attr({'rel':'tooltip', 'title':'Wash station'});
    }
    var tableList = $.parseJSON(data);
    for (var x = 0; x < tableList.length; x++) {
        var arr = tableList[x];
        var name = arr[0];
        var grid = arr[1][0];
        var site = arr[1][1] + 1;
        var plate = arr[2];

        $("#row" + site).children("#" + grid).append('<div id="plate-nickname">' + name + '</div><div id="plate-name">' + plate + '</div>').addClass('grid-active');

        if (plate.substring(0, 2) == '24') {
            $("#row" + site).children("#" + grid).addClass('wells24');
            SetPlateSize(grid, site)
        }
        if (plate.substring(0, 2) == '96') {
            $("#row" + site).children("#" + grid).addClass('wells96');
            SetPlateSize(grid, site)
        }
        if (plate.substring(0, 2) == '38') {
            $("#row" + site).children("#" + grid).addClass('wells384');
            SetPlateSize(grid, site)
        }
        if (plate.substring(0, 4) == 'Tube') {
            $("#row" + site).siblings().children("#" + (grid)).addClass('grid-active');
            $("*").children("#" + grid).attr({'rel':'tooltip', 'title':name + '<br />' + plate}).addClass('grid-tube');
        }
        if (plate.substring(0, 4) == 'REMP') {
            SetPlateSize(grid, site)
        }
        if (plate.substring(0, 5) == 'Te-PS') {
            SetPlateSize(grid, site)
        }
        if (plate.substring(0, 9) == 'Trough 60') {
            SetPlateSize(grid, site)
        }
        if (plate.substring(0, 10) == 'Trough 300') {
            for (var g = 1; g < 6; g++) {
                $("#row" + site).children("#" + (grid + g)).remove();
            }
            $("#row" + site).children("#" + grid).addClass('grid-plate');
        }
        if ($("#row" + site).children("#" + grid).css('width') == '13px') {
            $("#row" + site).children("#" + grid).children('#plate-name').remove().children('#plate-nickname').addClass('rotate');
        }
        $("#row" + site).children("#" + grid).attr({'rel':'tooltip', 'title':name + '<br />' + plate});
        $("[rel=tooltip]").tooltip({'placement':'bottom', 'trigger':'hover'});
    }
}

function SetPlateSize(grid, site) {
    for (var g = 1; g < 6; g++) {
        $("#row" + site).children("#" + (grid + g)).remove();
    }
    $("#row" + site).children("#" + grid).addClass('grid-plate');
}

function removeDuplicates(arr) {
    var i,
        len = arr.length,
        out = [],
        obj = {};

    for (i = 0; i < len; i++) {
        obj[arr[i]] = 0;
    }
    for (i in obj) {
        //noinspection JSUnfilteredForInLoop
        out.push(i);
    }
    return out;
}

var methods = [''];
function customizeMethods() {
    var method = $('#userMethod').val();
    if (method) {
        method = method.replace(' ', '');
        if (methods.indexOf(method) == -1) {
            methods.push(method);
            var me = method;
            $('#newMethod').after('<div class="label method" id="' + me + '" onclick="makeDefault(\'' + me + '\')">' + me + '<i class="icon-remove icon-white pull-right" onclick="removeMethod(\'' + me + '\');"></i></div>');
            $('#userMethod').val('');
            $('#methodsList').val(methods);
        }
    }
}

function removeMethod(method) {
    if (!e) var e = window.event;
    e.cancelBubble = true;
    if (e.stopPropagation) e.stopPropagation();
    methods = $('#methodsList').val().split(',');
    var ind = methods.indexOf(method);
    methods.splice(ind, 1);
    $('#' + method).remove();
    if (methods.length > 0) {
        makeDefault(methods[0])
    }
    else {
        $('#methodsList').val(methods);
    }
}

function makeDefault(method) {
    console.log(methods);
    $('.method').removeClass('label-info');
    $('#prpr-default').remove();
    $('#' + method).addClass('label-info');
    $('#' + method).append('<i class="icon-star icon-white pull-right" id="prpr-default"></i>');
    var ind = methods.indexOf(method);
    methods.splice(ind, 1);
    methods.unshift(method);
    $('#methodsList').val(methods);
}