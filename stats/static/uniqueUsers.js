function onFormLoad(){
    periodSelect()
    addFormListeners();
}
function addFormListeners(){
    const form = document.querySelector('form');
    const radioButtons = document.querySelectorAll('input[type="radio"]');
    radioButtons.forEach( button => {
        button.addEventListener('click', radioClick)
    });
}

function radioClick(ev){
    const btn = ev.target;
    const clientSelector = document.getElementById('id_client');
    const periodStart = document.getElementById('id_period_start');
    const periodEnd = document.getElementById('id_period_end');
    if (btn.id == 'id_scope_select_0'){
        clientSelector.removeAttribute('disabled')
    } else if (btn.id == 'id_scope_select_1'){
        clientSelector.disabled=true;
    } else if (btn.id == 'id_period_select_0'){
        periodStart.removeAttribute('disabled')
        periodEnd.disabled=true;
        periodEnd.value='';
    } else if (btn.id == 'id_period_select_1'){
        periodStart.removeAttribute('disabled')
        periodEnd.removeAttribute('disabled')
        // periodEnd.disabled=false
    } else if (btn.id == 'id_period_select_2'){
        periodStart.disabled=true;
        periodEnd.disabled=true;
    }
}

function periodSelect(){
    const forPeriod = document.getElementById('id_period_select_0');
    const forRange = document.getElementById('id_period_select_1');
    const forAll = document.getElementById('id_period_select_2');
    const periodStart = document.getElementById('id_period_start');
    const periodEnd = document.getElementById('id_period_end');

    if (forPeriod.hasAttribute('checked')){
        periodStart.removeAttribute('disabled')
        periodEnd.disabled=true;
        periodEnd.value='';
    } else if (forRange.hasAttribute('checked')){
        periodStart.removeAttribute('disabled')
        periodEnd.removeAttribute('disabled')
        // periodEnd.disabled=false
    } else if (forAll.hasAttribute('checked')){
        periodStart.disabled=true;
        periodEnd.disabled=true;
    }
}

window.onload = onFormLoad();
