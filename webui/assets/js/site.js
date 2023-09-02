const EMPTYSTR = '';
const APIGuide = {
    "Cluster": {
        "path": "/libreapi/cluster"
    },
    // BASE
    "NetAlias": {
        "path": "/libreapi/base/netalias",
        "presentation-html": "netalias-table",
        "sample": {
            "name": "netalias_name",
            "desc": "description",
            "addresses": [
                {
                    "member": "nodeid",
                    "listen": "listen_ip_address",
                    "advertise": "advertise_ip_address"
                }
            ]
        }
    },
    "AccessControl": {
        "path": "/libreapi/base/acl",
        "presentation-html": "acl-table",
        "sample": {
            "name": "acl_name",
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
        "presentation-html": "media-class-table",
        "sample": {
            "name": "media_class_name",
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
        "presentation-html": "capacity-class-table",
        "sample": {
            "name":"capacity_class_name",
            "desc": "description",
            "cps": -1,
            "concurentcalls": -1
        }
    },
    "TranslationClass": {
        "path": "/libreapi/class/translation",
        "presentation-html": "translation-class-table",
        "sample": {
            "name":"translation_class_name",
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
        "presentation-html": "manipulation-class-table",
        "sample": {
            "name":"manipulation_class_name",
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
        "presentation-html": "preanswer-class-table",
        "sample": {
            "name": "preanswer_class_name",
            "desc": "description",
            "streams": [
                {
                    "type": "signal/tone/media/speak",
                    "stream": "ring_ready/tone/mediafile"
                }
            ]
        }
    },
    // INTERCONECTION
    "SIPProfile": {
        "path": "/libreapi/sipprofile",
        "presentation-html": "sipprofile-table",
        "sample": {
            "name": "sip_profile_name",
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
            "sip_address": "netalias_name",
            "rtp_address": "netalias_name",
            "tls": false,
            "tls_only": false,
            "sips_port": 5061,
            "tls_version": "tlsv1.2"
        }
    },
    "Inbound": {
        "path": "/libreapi/interconnection/inbound",
        "presentation-html": "inbound-intcon-table",
        "sample": {
            "name": "inbound_interconnection_name",
            "desc": "description",
            "sipprofile": "sip_profile_name",
            "routing": "routing_table_name",
            "sipaddrs": [
                "farend_sip_signaling_ip_network_address"
            ],
            "rtpaddrs": [
                "farend_rtp_media_ip_network_address"
            ],
            "ringready": false,
            "media_class": "media_class",
            "capacity_class": "capacity_class",
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
        "presentation-html": "outbound-intcon-table",
        "sample": {
            "name": "outbound_interconnection_name",
            "desc": "description",
            "sipprofile": "sip_profile_name",
            "rtpaddrs": [
                "farend_rtp_media_ip_network_address"
            ],
            "media_class": "media_class",
            "capacity_class": "capacity_class",
            "translation_classes": [],
            "manipulation_classes": [],
            "privacy": [
                "none"
            ],
            "cid_type": "none",
            "distribution": "weight_based",
            "gateways": [
              {
                "name": "gateway_name",
                "weight": 1
              }
            ],
            "nodes": [
                "_ALL_"
            ],
            "enable": true,
        }
    },
    "Gateway": {
        "path": "/libreapi/base/gateway",
        "presentation-html": "gateway-table",
        "sample":{
            "name": "gateway_name",
            "desc": "description",
            "username": "none",
            "password": "none",
            "proxy": "farend_sip_signaling_ip_address",
            "port": 5060,
            "transport": "udp",
            "do_register": false,
            "caller_id_in_from": true,
            "cid_type": "none",
            "ping": 600
        }
    },
    // ACCESS LAYER
    "AccessService": {
        "path": "/libreapi/access/service",
        "presentation-html": "access-service-table",
        "sample": {
            "name": "name",
            "desc": "description",
            "trying_reason": "LibreSBC Trying",
            "natping_from": "sip:keepalive@libresbc",
            "topology_hiding": "hide.topo",
            "whiteips":[],
            "blackips":[],
            "antiflooding": {
                "sampling": 2,
                "density": 20,
                "window": 600,
                "threshold": 3,
                "bantime": 600
            },
            "authfailure": {
                "window": 600,
                "threshold": 18,
                "bantime": 900
            },
            "attackavoid": {
                "window": 18000,
                "threshold": 3,
                "bantime": 7200
            },
            "transports": [
                "udp",
                "tcp"
            ],
            "sip_address": "netalias_name",
            "domains": [
                "libre.sbc"
            ]
        }
    },
    "AccessDomainPolicy": {
        "path": "/libreapi/access/domain-policy",
        "presentation-html": "access-domain-presentation-object",
        "sample": {
            "domain": "libre.sbc",
            "srcsocket": {
                "ip": "127.0.0.3"
            },
            "dstsocket": {
                "ip": "127.0.0.2"
            }
        }
    },
    "AccessUserDirectory": {
        "path": "/libreapi/access/directory/user",
        "presentation-html": null,
        "sample": {
            "domain": "libre.sbc",
            "id": "joebiden",
            "secret": "p@ssword"
        }
    },
    // ROUTING
    "RoutingTable": {
        "path": "/libreapi/routing/table",
        "presentation-html": "routing-presentation-object",
        "sample": 	{
            "name": "routing_table_name",
            "desc": "description",
            "action": "route/block/query/httpr",
            "variables": ["cidnumber", "cidname", "dstnumber", "intconname", "realm"],
            "routes": {
                "primary": "primary_endpoint",
                "secondary": "secondary_endpoint",
                "load": 100
            }
        }
    },
    "RoutingRecord": {
        "path": "/libreapi/routing/record",
        "presentation-html": null,
        "sample": 	{
            "table": "routing_table_name",
            "match": "em/lpm/eq/ne/gt/lt",
            "value": "reference_value",
            "action": "route/block/jumps",
            "routes": {
                "primary": "primary_endpoint",
                "secondary": "secondary_endpoint",
                "load": 50
            }
        }
    },
};

var ConfigDetailTextH = document.getElementById("config-detail");
var ConfigSubmitBntH = document.getElementById("config-submit");
var PanelLabelH = document.getElementById("offcanvaspanel-label");
var offcanvaspanel;
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))
/*---------------------------------------------------------------------------*/

function GetPresentNode(){
    $.ajax({
        type: "GET",
        url: '/libreapi/predefine',
        success: function (data) {
            ShowProgress();
            let CandidateHtml = EMPTYSTR;
            data.candidates.forEach((element) => {
                CandidateHtml = `${CandidateHtml}<span class="badge bg-secondary rounded-pill" id="cdr-bucket">${element}</span>`;
            });
            document.getElementById('node-info').innerHTML = `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                Software Version <span class="badge bg-success rounded-pill">${data.swversion}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                NodeID <span class="badge bg-danger rounded-pill">${data.nodeid}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                Node Candidates
                <div>${CandidateHtml}</div></li>`;
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            document.getElementById('node-info').innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });

    $.ajax({
        type: "GET",
        url: '/libreapi/cluster',
        success: function (data) {
            ShowProgress();
            let MembersHtml = EMPTYSTR;
            data.members.forEach((element) => {
                MembersHtml = `${MembersHtml}<span class="badge bg-dark rounded-pill" id="cdr-bucket">${element}</span>`;
            });
            document.getElementById('cluster-info').innerHTML = `
            <li class="list-group-item d-flex justify-content-between align-items-center">
            Cluster Name <span class="badge bg-warning text-dark rounded-pill">${data.name}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between align-items-center">
                Members
                <div>
                ${MembersHtml}
                </div>
            </li>
            <li class="list-group-item d-flex justify-content-between align-items-center">
                Soft Capacity
                <div>
                <span class="badge bg-primary rounded-pill">cps: ${data.max_calls_per_second}</span>
                <span class="badge bg-primary rounded-pill">concurrent call: ${data.max_concurrent_calls}</span>
                </div>
            </li>
            <li class="list-group-item d-flex justify-content-between align-items-center">
                RTP Ranges
                <div>
                <span class="badge bg-light text-dark rounded-pill" id="cdr-bucket">${data.rtp_start_port}-${data.rtp_end_port}</span>
            </div>`;
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            document.getElementById('cluster-info').innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

function GeneralGetPresent(SettingName){
    let path = APIGuide[SettingName]['path']
    let presentation = APIGuide[SettingName]["presentation-html"]
    $.ajax({
        type: "GET",
        url: path,
        success: function (data) {
            ShowProgress();
            if (SettingName === 'RoutingTable'){
                RoutingTablePresentData(data, presentation);
            }
            else if (SettingName === 'AccessDomainPolicy'){
                AccessDomainPresentData(data, presentation);
            }
            else{
                GeneralPresentData(data, SettingName, presentation);
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            document.getElementById(presentation).innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

function GeneralPresentData(DataList, SettingName, presentation){
    let tablebody = EMPTYSTR;
    let cnt = 1;
    DataList.forEach((element) => {
        let name = element.name;
        let desc = element.desc;
        htmltb = `
        <tr>
        <td>${cnt}</td>
        <td>${name}</td>
        <td>${desc}</td>
        <td>
          <button class="btn btn-danger btn-sm" type="button"><i class="fa fa-times-circle" onclick="GeneralRemove('${name}','${SettingName}')"></i></button>
          <button class="btn btn-success btn-sm" type="button"><i class="fa fa-pencil" onclick="GeneralModify('${name}','${SettingName}')"></i></button>
        </td>
        </tr>`;
        tablebody = tablebody + htmltb;
        cnt++;
    });
    document.getElementById(presentation).innerHTML = `
        <table class="table">
          <thead class="table-light">
          <tr>
            <th scope="col">#</th>
            <th scope="col">Name</th>
            <th scope="col">Description</th>
            <th scope="col"> </th>
          </tr>
          </thead>
          <tbody>
            ${tablebody}
          </tbody>
        </table>`;
}

// remove button
function GeneralRemove(name, SettingName){
    let path = APIGuide[SettingName]['path']
    $.ajax({
        type: "DELETE",
        url: `${path}/${name}`,
        success: function (data) {
            ShowToast(`Delete Successfully ${SettingName} ${name}`, "info");
            ShowProgress();
            GeneralGetPresent(SettingName);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

// modify/update button
function GeneralModify(name, SettingName){
    ShowProgress();
    let path = APIGuide[SettingName]['path']
    let url = APIGuide[SettingName]['path'] + "/" + name
    if (name===EMPTYSTR) {
        url = path;
    }
    $.ajax({
        type: "GET",
        url: url,
        success: function (data) {
            ShowToast(`Detailize Successfully ${SettingName} ${name}`, "info");
            // canvas
            if (SettingName === 'AccessDomainPolicy'){
                PresentCanvas(data, name, SettingName, 'PATCH');
            }else{
                PresentCanvas(data, name, SettingName, 'PUT');
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

// submit button in canvas
function GeneralSubmit(name, SettingName, method="POST"){
    let path = APIGuide[SettingName]['path'];
    let jsonstring = ConfigDetailTextH.value;

    // create or update
    let url = path;
    if (method === 'PUT'){
        url = `${path}/${name}`
    }
    if (name===EMPTYSTR) {
        url = path;
    }

    // for modify special API such as [cluster]
    if (SettingName==='RoutingRecord') {
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
            if (SettingName === 'Cluster'){
                GetPresentNode();
            } else if (SettingName === 'RoutingRecord') {
                RoutingTableDetail(name);
            } else if (SettingName === 'AccessUserDirectory'){
                AccessUserDirectoryDetail(name);
            } else {
                GeneralGetPresent(SettingName);
            }
            offcanvaspanel.hide();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

// create button
function GeneralCreate(SettingName, ObjectName=EMPTYSTR){
    let sample = APIGuide[SettingName]['sample'];
    if (SettingName === 'RoutingRecord'){
        sample['table'] = ObjectName;
    }
    // canvas
    PresentCanvas(sample, ObjectName, SettingName, 'POST');
}

// --------------------------------------------------
// ACCESS DOMAIN
// --------------------------------------------------

// Access domain policy+user presentation
function AccessDomainPresentData(data, presentation){
    let AccessDomainHtml = EMPTYSTR;
    let cnt = 0;
    data.forEach((Adomain) => {
        adomainhtml = `
        <div class="accordion-item">
          <h2 class="accordion-header" data-bs-title="show detail">
            <button class="accordion-button collapsed" data-bs-toggle="collapse" data-bs-target="#collapseAD${Adomain}">
              <span class="badge rounded-pill text-bg-primary">${cnt}</span>&nbsp;&nbsp;
              <span class="text-primary fw-bolder">${Adomain}</span>
            </button>
          </h2>
        <div id="collapseAD${Adomain}" class="accordion-collapse collapse">
          <div class="accordion-body">
            <div class="row">
              <div class="col-md-6 col-lg-6">
                <div class="row">
                  <div class="btn-group" role="group">
                    <button type="button" class="btn btn-outline-primary text-start" onclick="AccessDomainPolicyDetail('${Adomain}')"><i class="fa fa-refresh"></i> Load Policy</button>
                    <button type="button" class="btn btn-outline-primary text-start" onclick="GeneralModify('${Adomain}','AccessDomainPolicy')"><i class="fa fa-pencil-square-o"></i> Update Policy</button>
                    <button type="button" class="btn btn-outline-danger text-start" onclick="GeneralRemove('${Adomain}','AccessDomainPolicy')"><i class="fa fa-trash"></i> Delete Policy</button>
                  </div>
                </div>
                <br>
                <div class="row">
                  <div class="col-md-12 col-lg-12" id="DetailAD${Adomain}"></div>
                </div>
              </div>
              <div class="col-md-6 col-lg-6">
                <div class="row g-3 justify-content-end">
                  <div class="col-md-6 col-lg-6">
                    <div class="btn-group" role="group">
                      <button type="button" class="btn btn-primary text-start" onclick="GeneralCreate('AccessUserDirectory','${Adomain}')"><i class="fa fa-plus-square-o"></i> Create User</button>
                      <button type="button" class="btn btn-primary text-start" onclick="AccessUserDirectoryDetail('${Adomain}')"><i class="fa fa-refresh"></i> Load Users</button>
                    </div>
                  </div>
                </div>
                <br>
                <div class="row">
                  <div class="col-md-12 col-lg-12" id="TableAD${Adomain}"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        </div>`
        AccessDomainHtml = AccessDomainHtml + adomainhtml;
        cnt = cnt+1;
    });
    document.getElementById(presentation).innerHTML = AccessDomainHtml;
}

// Access domain policy show detail
function AccessDomainPolicyDetail(Adomain){
    $.ajax({
        type: "GET",
        url: `/libreapi/access/domain-policy/${Adomain}`,
        success: function (data) {
            ShowProgress();
            document.getElementById(`DetailAD${Adomain}`).innerHTML = `
            <div class="card border-primary">
              <div class="card-body text-primary">
                <pre><code>${JSON.stringify(data, undefined, 4)}</code></pre>
              </div>
            </div>`;
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            document.getElementById(`DetailAD${Adomain}`).innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

// Access user directory list all user
function AccessUserDirectoryDetail(Adomain){
    $.ajax({
        type: "GET",
        url: `/libreapi/access/directory/user/${Adomain}`,
        success: function (data) {
            ShowProgress();
            let usertable = EMPTYSTR;
            let cnt = 1;
            users = [];
            if (Adomain in data){
                users = data[Adomain];
            }
            users.forEach((user)=>{
                userhtml = `
                <tr>
                  <td>${cnt}</td> <td>${user}</td>
                  <td>
                    <button class="btn btn-danger btn-sm" type="button"><i class="fa fa-times-circle" onclick="RemoveAccessUser('${Adomain}','${user}')"></i></button>
                    <button class="btn btn-success btn-sm" type="button"><i class="fa fa-pencil" onclick="UpdateAccessUser('${Adomain}','${user}')"></i></button>
                  </td>
                </tr>`;
                usertable = usertable + userhtml;
                cnt++;
            });
            if (users.length!==0){
                document.getElementById(`TableAD${Adomain}`).innerHTML = `
                <table class="table table-hover">
                <thead class="table-light">
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">User</th>
                  <th scope="col"></th>
                </tr>
                </thead>
                  <tbody>
                  ${usertable}
                  </tbody>
                </table>`;
            } else {
                document.getElementById(`TableAD${Adomain}`).innerHTML = EMPTYSTR;
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            document.getElementById(`TableAD${Adomain}`).innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

// Access user directory remove user
function RemoveAccessUser(domain, user){
    let SettingName = 'AccessUserDirectory';
    let path = APIGuide[SettingName]['path']
    $.ajax({
        type: "DELETE",
        url: `${path}/${domain}/${user}`,
        success: function (data) {
            ShowToast(`Delete Successfully ${SettingName} ${user}@${domain}`, "info");
            ShowProgress();
            AccessUserDirectoryDetail(domain);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

// Access user directory partial update user
function UpdateAccessUser(domain, user){
    ShowProgress();
    let SettingName = 'AccessUserDirectory';
    let url = APIGuide[SettingName]['path'] + "/" + domain + "/" + user;
    $.ajax({
        type: "GET",
        url: url,
        success: function (data) {
            let userdata = {
                "domain": domain,
                "id": user,
                "secret": data.secret
            };
            ShowToast(`Detailize Successfully ${SettingName} ${user}@${domain}`, "info");
            // canvas
            PresentCanvas(userdata, domain, SettingName, 'PATCH');
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

// -------------------------------------------------//
// --   Routing                                     //
// -------------------------------------------------//
function RoutingTablePresentData(data, presentation){
    let RoutingTablesHtml = EMPTYSTR;
    data.forEach((Rtable) => {
        let rtbName = Rtable.name;
        let rtbAction = Rtable.action;
        let rtbDesc = Rtable.desc;

        let newRecordButton = EMPTYSTR;
        if (rtbAction === 'query'){
            newRecordButton = `<button type="button" class="btn btn-outline-primary text-start" onclick="GeneralCreate('RoutingRecord','${rtbName}')"><i class="fa fa-plus-square-o"></i> Create Record</button>`;
        }

        rtblhtml = `
        <div class="accordion-item">
        <h2 class="accordion-header" data-bs-title="show detail">
          <button class="accordion-button collapsed" data-bs-toggle="collapse" data-bs-target="#collapseRT${rtbName}">
            <span class="text-primary fw-bolder">${rtbName}</span> &nbsp;&nbsp;
            <span class="badge rounded-pill text-bg-danger">${rtbAction}</span> &nbsp;&nbsp; ${rtbDesc}</button>
        </h2>
        <div id="collapseRT${rtbName}" class="accordion-collapse collapse">
          <div class="accordion-body">
            <div class="row">
              <div class="col-md-4 col-lg-4">
                <div class="btn-group-vertical" role="group">
                  <button type="button" class="btn btn-outline-primary text-start" onclick="RoutingTableDetail('${rtbName}')"><i class="fa fa-refresh"></i> Load Table</button>
                  <button type="button" class="btn btn-outline-primary text-start" onclick="GeneralModify('${rtbName}','RoutingTable')"><i class="fa fa-pencil-square-o"></i> Update Table</button>
                  <button type="button" class="btn btn-outline-danger text-start" onclick="GeneralRemove('${rtbName}','RoutingTable')"><i class="fa fa-trash"></i> Delete Table</button>
                  ${newRecordButton}
                </div>
              </div>
              <div class="col-md-8 col-lg-8" id="DetailRT${rtbName}">
              </div>
            </div>
            <br>
            <div class="row" id="TableRR${rtbName}">
            </div>
          </div>
        </div>
        </div>`
        RoutingTablesHtml = RoutingTablesHtml + rtblhtml;
    });
    document.getElementById(presentation).innerHTML = RoutingTablesHtml;
}

function RoutingTableDetail(Rtablename){
    $.ajax({
        type: "GET",
        url: `/libreapi/routing/table/${Rtablename}`,
        success: function (data) {
            ShowProgress();
            records = data.records;
            delete data['records'];
            document.getElementById(`DetailRT${Rtablename}`).innerHTML = `
            <div class="card border-primary">
              <div class="card-body text-primary">
                <pre><code>${JSON.stringify(data, undefined, 4)}</code></pre>
              </div>
            </div>`;
            // routing record
            let recordtable = EMPTYSTR;
            let cnt = 1;
            records.forEach((record)=>{
                let action = record.action;
                let match = record.match;
                let value = record.value;
                let primary = EMPTYSTR;
                let secondary = EMPTYSTR;
                let load = EMPTYSTR;
                if (action!=='block'){
                    primary = record.routes.primary;
                    secondary = record.routes.secondary;
                    load = record.routes.load;
                }
                recordhtml = `
                <tr>
                  <td>${cnt}</td> <td>${match}</td> <td>${value}</td> <td>${action}</td> <td>${primary}</td> <td>${secondary}</td> <td>${load}</td>
                  <td>
                    <button class="btn btn-danger btn-sm" type="button"><i class="fa fa-times-circle" onclick="RemoveRoutingRecord('${Rtablename}','${match}','${value}')"></i></button>
                    <button class="btn btn-success btn-sm" type="button"><i class="fa fa-pencil" onclick="UpdateRoutingRecord('${Rtablename}','${match}','${value}','${action}','${primary}','${secondary}','${load}')"></i></button>
                  </td>
                </tr>`;
                recordtable = recordtable + recordhtml;
                cnt++;
            });
            if (records.length!==0){
                document.getElementById(`TableRR${Rtablename}`).innerHTML = `
                <table class="table table-bordered">
                <thead class="table-light">
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">Match</th>
                  <th scope="col">Value</th>
                  <th scope="col">Action</th>
                  <th scope="col">Primary</th>
                  <th scope="col">Secondary</th>
                  <th scope="col">Load</th>
                  <th scope="col"></th>
                </tr>
                </thead>
                  <tbody>
                  ${recordtable}
                  </tbody>
                </table>`;
            };
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            document.getElementById("DetailRT"+Rtablename).innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

function RemoveRoutingRecord(tablename, match, value){
    let SettingName = 'RoutingRecord';
    let path = APIGuide[SettingName]['path']
    $.ajax({
        type: "DELETE",
        url: `${path}/${tablename}/${match}/${value}`,
        success: function (data) {
            ShowToast(`Delete Successfully ${SettingName} ${tablename} ${match} ${value}`, "info");
            ShowProgress();
            RoutingTableDetail(tablename);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

function UpdateRoutingRecord(tablename, match, value, action, primary, secondary, load){
    ShowProgress();
    let SettingName = 'RoutingRecord';
    let record = {
        "table": tablename,
        "match": match,
        "value": value,
        "action": action,
    }
    if (action!=='block'){
        record['routes'] = {
            "primary": primary,
            "secondary": secondary,
            "load": load
        }
    }
    ShowToast(`Detailize Successfully ${SettingName} ${tablename}`, "info");
    // canvas
    PresentCanvas(record, tablename, SettingName, 'PUT');
}

/* ----------------------- */
function PresentCanvas(Data, ObjectName, SettingName, method){
    ConfigDetailTextH.value = JSON.stringify(Data, undefined, 4);
    PanelLabelH.innerHTML = `${SettingName}  <strong><code>${ObjectName}</code></strong>`;
    ConfigSubmitBntH.setAttribute('onclick',`GeneralSubmit('${ObjectName}','${SettingName}','${method}')`);

    var OffCanvasHtml = document.getElementById("offcanvaspanel");
    offcanvaspanel = new bootstrap.Offcanvas(OffCanvasHtml);
    offcanvaspanel.show();
}

function PrettyCode(){
    //
    // https://github.com/WebReflection/highlighted-code
    //
    (async ({chrome, netscape}) => {
        // add Safari polyfill if needed
        if (!chrome && !netscape)
          await import('https://unpkg.com/@ungap/custom-elements');

        const {default: HighlightedCode} =
          await import('https://unpkg.com/highlighted-code');

        // bootstrap a theme through one of these names
        // https://github.com/highlightjs/highlight.js/tree/main/src/styles
        HighlightedCode.useTheme('monokai-sublime'); //intellij-light,monokai-sublime/googlecode/idea/github
    })(self);
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
