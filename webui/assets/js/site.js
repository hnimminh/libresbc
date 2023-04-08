const EMPTYSTR = '';
var GroupItemELMS = document.getElementById('AccordionGroupItems');
var ProgressDotELMS = document.getElementById('progessdot');
var EventMessageEMLS = document.getElementById('event-message');
var ToastMsgEMLS = document.getElementById('toastmsg');
/*---------------------------------------------------------------------------*/
function InitialPage(){
    ListInstances();
}

/* ---------------------------------------------------------------------------
    INSTANCE SERVICES
--------------------------------------------------------------------------- */
function ListData(){
    $.ajax({
        type: "GET",
        url: "/service ",
        success: function (data) {
            ShowProgress();
            PresentInstance(data);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            GroupItemELMS.innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

function PresentData(DataList){
    let htmlitems = EMPTYSTR;
    let cnt = 1;
    DataList.forEach((element) => {
        let expires = element.expires
        let ttl = expires - (Math.floor(Date.now() / 1000) - Number(element.timestamp))
        let htmlitem = `<div class="accordion-item">
        <h2 class="accordion-header" id="flush-heading`+cnt+`">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#flush-collapse`+cnt+`" aria-expanded="false" aria-controls="flush-collapse`+cnt+`">
            <div class="lead">
                <span class="badge bg-primary rounded-pill">ipaddr: `+element.ipaddr+`</span>
                <span class="badge bg-warning text-dark rounded-pill">role: `+element.role+`</span>
                <span class="badge bg-success rounded-pill">swtype: `+element.swtype+`</span>
                <span class="badge bg-danger rounded-pill">expires: `+ttl+`/`+expires+`</span>
            </div>
            </button>
        </h2>
        <div id="flush-collapse`+cnt+`" class="accordion-collapse collapse" aria-labelledby="flush-heading`+cnt+`">
            <div class="accordion-body">
                <code><pre id="instance-data-`+cnt+`">`+JSON.stringify(element, undefined, 4)+`</pre></code>
            </div>
            <div class="btn-group" role="group">
                <button type="button" class="btn btn-outline-primary" onclick="TerminateInstance(`+cnt+`);">Soft Terminate</button>
                <button type="button" class="btn btn-outline-primary" data-bs-toggle="offcanvas" data-bs-target="#offcanvasBottom" aria-controls="offcanvasBottom" onclick="CallStatus(`+cnt+`);">Call Status</button>
            </div><br><br>
        </div>
        </div>`;
        htmlitems = htmlitems + htmlitem;
        cnt++;
    });
    GroupItemELMS.innerHTML = htmlitems;
}

/* ---------------------------------------------------------------------------
    PROGRESS STATE
--------------------------------------------------------------------------- */
function ShowProgress(){
    ProgressDotELMS.classList.remove('invisible');
    setTimeout(function() {ProgressDotELMS.classList.add('invisible')}, 777);
}

function ShowToast(message, msgtype='danger'){
    if (msgtype === 'danger'){
        ToastMsgEMLS.classList.add('bg-danger');
        ToastMsgEMLS.classList.remove('bg-primary');
        ToastMsgEMLS.classList.remove('bg-warning');
        ToastMsgEMLS.classList.remove('bg-success');
    } else if (msgtype === 'success'){
        ToastMsgEMLS.classList.add('bg-success');
        ToastMsgEMLS.classList.remove('bg-primary');
        ToastMsgEMLS.classList.remove('bg-danger');
        ToastMsgEMLS.classList.remove('bg-warning');
    }  else if (msgtype === 'warning'){
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
    EventMessageEMLS.innerHTML = message;
    $('.toast').toast('show');
}
