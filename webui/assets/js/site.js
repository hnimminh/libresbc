const EMPTYSTR = '';
var BaseNetAliasTableELMS = document.getElementById('base-netalias-table');
var ProgressDotELMS = document.getElementById('progessdot');
var EventMessageEMLS = document.getElementById('event-message');
var ToastMsgEMLS = document.getElementById('toastmsg');
/*---------------------------------------------------------------------------*/
function InitialPage(){
}

/* ---------------------------------------------------------------------------
    BASE CONFIG
--------------------------------------------------------------------------- */

function GetBaseCfg() {
    GetandPresentNetAlias();
}

function GetandPresentNetAlias(){
    $.ajax({
        type: "GET",
        url: "/libreapi/base/netalias",
        success: function (data) {
            ShowProgress();
            PresentData(data);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            BaseNetAliasTableELMS.innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });
}

function PresentData(DataList){
    let tablebody = EMPTYSTR;
    let cnt = 1;
    DataList.forEach((element) => {
        htmltb = `<tr>
                    <td>`+cnt+`</td>
                    <td>`+element.name+`</td>
                    <td>`+element.desc+`</td>
                    <td>
                      <button class="btn btn-primary btn-sm" type="button"><i class="fa fa-pencil" onclick="RemoveNetAlias(`+element.name+`)"></i></button>
                      <button class="btn btn-danger btn-sm" type="button"><i class="fa fa-times-circle"></i></button>
                    </td>
                  </tr>`
        tablebody = tablebody + htmltb
        cnt++;
    });
    BaseNetAliasTableELMS.innerHTML = `
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

function RemoveNetAlias(name){
    $.ajax({
        type: "DELETE",
        url: "/libreapi/base/netalias/"+name,
        success: function (data) {
            ShowProgress();
            PresentData(data);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            BaseNetAliasTableELMS.innerHTML = EMPTYSTR;
            ShowToast(jqXHR.responseJSON.error);
        }
    });
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
