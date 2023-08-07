const DUMMY = 'DUMMY'
const EMPTYSTR = '';
const APIGuide = {
    "NetAlias": {
        "path": "/libreapi/base/netalias",
        "tablename": "base-netalias-table",
        "sample": {
            "name": "name",
            "desc": "description",
            "addresses": [
                {
                    "member": "nodeid",
                    "listen": "ip_address",
                    "advertise": "ip_address"
                }
            ]
        }
    },
    "AccessControl": {
        "path": "/libreapi/base/acl",
        "tablename": "base-accesscontrol-table",
        "sample": {
            "name": "name",
            "desc": "description",
            "action": "deny",
            "rules": [
                {
                    "action": "allow",
                    "key": "cidr",
                    "value": "ip_network_address"
                }
            ]
        }
    }
}

var ConfigDetailTextH = document.getElementById("config-detail");
var ConfigSubmitBntH = document.getElementById("config-submit");

var PanelLabelH = document.getElementById("offcanvaspanel-label");
/*---------------------------------------------------------------------------*/
function InitialPage(){
    GetBaseCfg();
}

/* ---------------------------------------------------------------------------
    BASE CONFIG
--------------------------------------------------------------------------- */

function GetBaseCfg() {
    GeneralGetPresent("NetAlias");
    GeneralGetPresent("AccessControl");
}

function GeneralGetPresent(SettingName){
    let path = APIGuide[SettingName]['path']
    let tablename = APIGuide[SettingName]['tablename']
    $.ajax({
        type: "GET",
        url: path,
        success: function (data) {
            ShowProgress();
            GeneralPresentData(data, SettingName, tablename);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            document.getElementById(tablename).innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

function GeneralPresentData(DataList, SettingName, tablename){
    let tablebody = EMPTYSTR;
    let cnt = 1;
    DataList.forEach((element) => {
        let name = element.name
        htmltb = `<tr>
                    <td>`+cnt+`</td>
                    <td>`+name+`</td>
                    <td>`+element.desc+`</td>
                    <td>
                      <button class="btn btn-danger btn-sm" type="button"><i class="fa fa-times-circle" onclick="GeneralRemove('`+name+`','`+SettingName+`')"></i></button>
                      <button class="btn btn-primary btn-sm" type="button">
                        <i class="fa fa-pencil" onclick="GeneralModify('`+name+`','`+SettingName+`')"></i>
                      </button>
                    </td>
                  </tr>`
        tablebody = tablebody + htmltb
        cnt++;
    });
    document.getElementById(tablename).innerHTML = `
        <table class="table">
        <thead>
        <tr>
            <th scope="col">#</th>
            <th scope="col">Name</th>
            <th scope="col">Description</th>
            <th scope="col">Action</th>
        </tr>
        </thead>
        <tbody>` + tablebody + `</tbody>
        </table>`;
}


function GeneralRemove(name, SettingName){
    let path = APIGuide[SettingName]['path']
    $.ajax({
        type: "DELETE",
        url: path + "/" + name,
        success: function (data) {
            ShowToast("Delete Successfully " + SettingName + " " + name, "info");
            ShowProgress();
            GeneralGetPresent(SettingName);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}


function GeneralModify(name, SettingName){
    ShowProgress();
    let path = APIGuide[SettingName]['path']
    $.ajax({
        type: "GET",
        url: path + "/" + name,
        success: function (data) {
            ShowToast("Detailize Successfully " + SettingName + " " + name, "info");
            ConfigDetailTextH.value = JSON.stringify(data, undefined, 4);
            PanelLabelH.innerHTML = SettingName + "  <strong><code>" + name + "</code></strong>";
            ConfigSubmitBntH.setAttribute('onclick',`GeneralSubmit('`+name+`','`+SettingName+`')`);

            var OffCanvasHtml = document.getElementById("offcanvaspanel");
            var offcanvaspanel = new bootstrap.Offcanvas(OffCanvasHtml);
            offcanvaspanel.show();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

function GeneralSubmit(name, SettingName){
    let path = APIGuide[SettingName]['path'];
    let jsonstring = ConfigDetailTextH.value;

    let method = 'PUT';
    let url = path + "/" + name
    if (name === DUMMY) {
        method = 'POST';
        url = path;
    }

    $.ajax({
        type: method,
        url: url,
        dataType: "json",
        contentType: 'application/json',
        data: jsonstring,
        success: function (data) {
            ShowToast("Data has been submited", "info");
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}


function GeneralCreate(SettingName){
    let sample = APIGuide[SettingName]['sample'];

    ConfigSubmitBntH.setAttribute('onclick',`GeneralSubmit('`+DUMMY+`','`+SettingName+`')`);
    ConfigDetailTextH.value = JSON.stringify(sample, undefined, 4);
    PanelLabelH.innerHTML = SettingName + "  <strong><code>" + EMPTYSTR + "</code></strong>";
    ConfigSubmitBntH.setAttribute('onclick',`GeneralSubmit('`+DUMMY+`','`+SettingName+`')`);

    var OffCanvasHtml = document.getElementById("offcanvaspanel");
    var offcanvaspanel = new bootstrap.Offcanvas(OffCanvasHtml);
    offcanvaspanel.show();
}

/* ---------------------------------------------------------------------------
    PROGRESS STATE
--------------------------------------------------------------------------- */
var ProgressDotELMS = document.getElementById('progessdot');
var ToastMsgEMLS = document.getElementById('toastmsg');

function ShowProgress(){
    ProgressDotELMS.classList.remove('invisible');
    setTimeout(function() {
        ProgressDotELMS.classList.add('invisible')
    },
    777);
}

function ShowToast(message, msgtype='danger'){
    if (msgtype === 'danger'){
        ToastMsgEMLS.classList.add('bg-danger');
        ToastMsgEMLS.classList.remove('bg-primary');
        ToastMsgEMLS.classList.remove('bg-warning');
        ToastMsgEMLS.classList.remove('bg-success');
    }else if (msgtype === 'success'){
        ToastMsgEMLS.classList.add('bg-success');
        ToastMsgEMLS.classList.remove('bg-primary');
        ToastMsgEMLS.classList.remove('bg-danger');
        ToastMsgEMLS.classList.remove('bg-warning');
    }else if (msgtype === 'warning'){
        ToastMsgEMLS.classList.add('bg-warning');
        ToastMsgEMLS.classList.remove('bg-primary');
        ToastMsgEMLS.classList.remove('bg-danger');
        ToastMsgEMLS.classList.remove('bg-success');
    }else {
        ToastMsgEMLS.classList.add('bg-primary');
        ToastMsgEMLS.classList.remove('bg-danger');
        ToastMsgEMLS.classList.remove('bg-warning');
        ToastMsgEMLS.classList.remove('bg-success');
    }
    document.getElementById('event-message').innerHTML = message;
    $('.toast').toast('show');
}
