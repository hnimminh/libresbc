const DUMMY = 'DUMMY'
const EMPTYSTR = '';
const APIGuide = {
    "NetAlias": {
        "path": "/libreapi/base/netalias",
        "tablename": "netalias-table",
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
        "tablename": "acl-table",
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
    },
    // CLASS
    "MediaClass": {
        "path": "/libreapi/class/media",
        "tablename": "media-class-table",
        "sample": {
            "name": "name",
            "desc": "description",
            "codecs": [
                "PCMA",
                "PCMU",
                "OPUS",
                "G729",
                "AMR-WB"
            ]
        }
    },
    "CapacityClass": {
        "path": "/libreapi/class/capacity",
        "tablename": "capacity-class-table",
        "sample": {
            "name":"name",
            "desc": "description",
            "cps": -1,
            "concurentcalls": -1
        }
    },
    "TranslationClass": {
        "path": "/libreapi/class/translation",
        "tablename": "translation-class-table",
        "sample": {
            "name":"name",
            "desc": "description",
            "caller_number_pattern": "^([0-9]+)$",
            "caller_number_replacement": "+%{1}",
            "destination_number_pattern": "",
            "destination_number_replacement": "",
            "caller_name": "_auto"
        }
    },
    "ManipulationClass": {
        "path": "/libreapi/class/manipulation",
        "tablename": "manipulation-class-table",
        "sample": {
            "name":"name",
            "desc": "description",
            "actions": [
                    {
                    "action": "action",
                    "targetvar": "variable",
                    "values": [
                        "value"
                    ]
                }
            ]
        }
    },
    "PreAnswerClass": {
        "path": "/libreapi/class/preanswer",
        "tablename": "preanswer-class-table",
        "sample": {
            "name": "name",
            "desc": "description",
            "streams": [
                {
                    "type": "signal/tone/media/speak",
                    "stream": "ring_ready/tone/mediafile"
                }
            ]
        }
    },
    // INTERCONCTION
    "SIPProfile": {
        "path": "/libreapi/sipprofile",
        "tablename": "sipprofile-table",
        "sample": {
            "name": "name",
            "desc": "description",
            "user_agent": "LibreSBC",
            "sdp_user": "LibreSBC",
            "local_network_acl": "rfc1918.auto",
            "enable_100rel": true,
            "ignore_183nosdp": true,
            "sip_options_respond_503_on_busy": false,
            "disable_transfer": true,
            "manual_redirect": true,
            "enable_3pcc": false,
            "enable_compact_headers": false,
            "dtmf_type": "rfc2833",
            "media_timeout": 0,
            "rtp_rewrite_timestamps": true,
            "context": "carrier",
            "sip_port": 5060,
            "addrdetect": "none",
            "sip_address": "netalias",
            "rtp_address": "netalias",
            "tls": false,
            "tls_only": false,
            "sips_port": 5061,
            "tls_version": "tlsv1.2"
        }
    },
    "Inbound": {
        "path": "/libreapi/interconnection/inbound",
        "tablename": "inbound-intcon-table",
        "sample": {
            "name": "name",
            "desc": "description",
            "sipprofile": "sipprofile",
            "routing": "routing-table",
            "sipaddrs": [
                "farend-sip-signaling-ip"
            ],
            "rtpaddrs": [
                "farend-rtp-media-ip"
            ],
            "ringready": false,
            "media_class": "media-class",
            "capacity_class": "capacity-class",
            "translation_classes": [],
            "manipulation_classes": [],
            "authscheme": "IP",
            "nodes": [
                "_ALL_"
            ],
            "enable": true
        }
    },
    "Outbound": {
        "path": "/libreapi/interconnection/outbound",
        "tablename": "outbound-intcon-table",
        "sample": {
            "name": "name",
            "desc": "description",
            "media_class": "media-class",
            "capacity_class": "capacity-class",
            "translation_classes": [],
            "manipulation_classes": [],
            "sipprofile": "gsipv6",
            "privacy": [
                "none"
            ],
            "cid_type": "none",
            "distribution": "weight_based",
            "gateways": [
              {
                "name": "HONEYPOT6GW",
                "weight": 1
              }
            ],
            "rtpaddrs": [
                "farend-rtp-media-ip"
            ],
            "nodes": [
                "_ALL_"
            ],
            "enable": true,
        }
    },
    "Gateway": {
        "path": "/libreapi/base/gateway",
        "tablename": "gateway-table",
        "sample":     {
            "name": "name",
            "desc": "description",
            "username": "none",
            "password": "none",
            "proxy": "farend-sip-signaling-ip",
            "port": 5060,
            "transport": "udp",
            "do_register": false,
            "caller_id_in_from": true,
            "cid_type": "none",
            "ping": "interval-in-second-for-sip-options"
        }
    },
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


function ShowConfigData(apis){
    let _apis = apis.split(",");
    for (var i = 0; i < _apis.length; i++) {
        GeneralGetPresent(_apis[i]);
    }
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
                      <button class="btn btn-success btn-sm" type="button">
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
