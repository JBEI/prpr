/**
 * parpar.js, a part of PaR-PaR, a biology-friendly language for liquid-transferring robots
 * Author: Nina Stawski, nstawski@lbl.gov, me@ninastawski.com
 * Copyright 2012, Lawrence Berkeley National Laboratory
 * http://github.com/JBEI/parpar/blob/master/license.txt
 */

function clicked() {
    var selection = $('#tables option:selected').val();
    if (selection == 'select') {
        $('#preview').remove();
        $('#table').append('<input type="file" name="data" id="data" class="span3" onchange="AppendUploadButton()"/>');
    }
    else {
        $('#data').remove();
        $('#preview').remove();
        $('#uploadFile').remove();
        $('#table').append('<button id="preview" class="btn btn-info pull-right" data-toggle="modal" href="#myModal" onclick="CallPython();">Preview table layout</button>');
    }
}

function AppendUploadButton() {
    $('#uploadFile').remove();
    $('#table').append('<button id="uploadFile" class="btn btn-info pull-right"  data-toggle="modal" href="#myModal" onclick="UploadTable();">Preview table layout</button>');
}

function LoadSampleScript() {
    $('#data').remove();
    $('#preview').remove();
    $('#uploadFile').remove();
    $('#table').append('<button id="preview" class="btn btn-info pull-right" data-toggle="modal" href="#myModal" onclick="CallPython();">Preview table layout</button>');
    $('#tables').val('BreakfastDrinks.ewt');
    $.post('sample', function(data) {
        $('#textarea').val(data);
    });
}

function UploadTable() {
    var file = $('#data')[0].files[0];
    var formData = new FormData();
    formData.append("file", file);
    $('#tablerow').children().remove();
    $.ajax({
        url: 'plates',
        type: 'POST',
        data: formData,
        cache: false,
        contentType: false,
        processData: false,
        success: function(data) {
            $('#platename').html(file.name);
            ParseTableData(data);
        }
    });
}

function CallPython() {
    var data = $('#tables option:selected').val();
    $('#tablerow').children().remove();
    $.post('table', data, function(data) {
        $('#platename').html($('#tables option:selected').val());
        ParseTableData(data);
    });
}

function ParseTableData(data) {
    for (var j=1; j <= 3; j++) {
        $('#tablerow').append('<div id="row' + j + '"></div>');

        for (var i=1; i <= 30; i++) {
            $('#row' + j).append('<div class="parpar-grid grid-empty" id="' + i + '"></div>');
        }
        $('#row' + j).children('#1').removeClass('grid-empty').addClass('grid-system').append('<div class="rotate">system</div>');
        $('#row' + j).children('#1').attr({'rel' : 'tooltip', 'title' : 'Wash station'});
    }
    var tableList = $.parseJSON(data);
    for (var x = 0; x < tableList.length; x++) {
        var arr = tableList[x];
        var name = arr[0];
        var grid = arr[1][0];
        var site = arr[1][1]+1;
        var plate = arr[2];

        $("#row" + site).children("#" + grid).append('<div id="plate-nickname">' + name + '</div><div id="plate-name">' + plate + '</div>');
        $("#row" + site).children("#" + grid).addClass('grid-active');

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
            $("*").children("#" + grid).attr({'rel' : 'tooltip', 'title' : name + '<br />' + plate});
            $("*").children("#" + grid).addClass('grid-tube');
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
            $("#row" + site).children("#" + grid).children('#plate-name').remove();
            $("#row" + site).children("#" + grid).children('#plate-nickname').addClass('rotate');
        }
        $("#row" + site).children("#" + grid).attr({'rel' : 'tooltip', 'title' : name + '<br />' + plate});
        $("[rel=tooltip]").tooltip({'placement' : 'bottom', 'trigger' : 'hover'});
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
        len=arr.length,
        out=[],
        obj={};

    for (i=0;i<len;i++) {
        obj[arr[i]]=0;
    }
    for (i in obj) {
        out.push(i);
    }
    return out;
}

var wellArray = Array();
var rID = 0;

function createPlates() {
    for (var i = 1; i <= 4; i++) {
        $('#plate').append('<div id="row' + i + '" class="parpar-row"></div>');
        for (var k = 1; k <= 6; k++) {
            var wellId = i + '' + k;
            $('#row' + i).append('<div id="well' + wellId + '" class="parpar-well" onclick="fillWell(' + wellId + ');"></div>');
        }

    }
}

function fillWell(wellId) {
    well = $('#well' + wellId);

    if (well.hasClass('parpar-well-taken')) {}

    else {
        well.toggleClass('parpar-well-filled');

        var wellLoc = '(' + wellId.toString().substr(0,1) + ',' + wellId.toString().substr(1,1) + ')';

        if (well.hasClass('parpar-well-filled')) {

            wellArray.push(wellId);
        }
        else {
            ind = wellArray.indexOf(wellId);
            wellArray.splice(ind,1);
        }

        if ($('#reagentName').val() != "") {
            reagentName = $('#reagentName').val();
        }
        else {
            reagentName = 'Reagent' + rID;
        }

        $('#loc').remove();

        $('#wellInfo').append('<div id="loc">' +
                                    '<div class="hidden" id="reagentLocation">' +
                                        wellArray.sort() +
                                    '</div>' +
                                    '<input type="text" class="input-xlarge" id="reagentName" value="' + reagentName + '">' +
                                    '</input>' +
                              '</div>');
    }
}

function addNew() {
    if ($('#reagentName').val() != "") {
        $('#reagents').append('<div class="btn" id="reagent' + rID +
            '" value="' + $('#reagentLocation').text() + '">' +
            $('#reagentName').val() + '</div> ');
        rID++;
        wellArray = [];
        $('.parpar-well-filled').addClass('parpar-well-taken').removeClass('parpar-well-filled');
        $('#loc').remove();
        $('#wellInfo').append('<div id="loc">' +
            '<input type="text" class="input-xlarge" id="reagentName" value="" />' +
            '</div>')
    }
}

function clearAll() {
    $('#reagents').children().remove();
    $('#loc').remove();
    $('#wellInfo').append('<div id="loc">' +
        '<input type="text" class="input-xlarge" id="reagentName" value="" />' +
        '</div>');
    $('.parpar-well').removeClass('parpar-well-taken').removeClass('parpar-well-filled');
}