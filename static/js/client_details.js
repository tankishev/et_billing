import {api} from "./api.js";
import {cleanModalForm, modalConfirmDelete, validateForm} from "./utils.js";

void setUp()

async function setUp(){
    sessionStorage.clear();
    document.querySelectorAll('#clientDetailsNav a')[0].classList.add('active');
    addListeners();
}

function addListeners(){
    document.addEventListener('show.bs.modal', (ev) => cleanModalForm(ev.target));
    const btnSave = document.getElementById('btnSave');
    const btnEdit = document.getElementById('btnEdit');
    const btnCancel = document.getElementById('btnCancel');
    const btnDelete = document.getElementById('btnDelete');
    const clientID = document.getElementById('client_id').value;

    const formFields = Array.from(document.querySelectorAll('form input, form select'));

    btnEdit.addEventListener('click', () => {
        btnCancel.parentElement.classList.remove('d-none');
        btnEdit.parentElement.classList.add('d-none');
        formFields.forEach(el => {
            el.removeAttribute('disabled')
        })
    })

    btnDelete.addEventListener('click', (ev)=>{
        ev.preventDefault();
        clientRemove(clientID);
    })

    btnCancel.addEventListener('click', async ()=>{
        const sessionData = sessionStorage.getItem('clientData');
        let data;
        if (sessionData === null){
            data = await api.clients.readClientDetails(clientID);
        } else {
            data = JSON.parse(sessionData)
        }
        if (data !== undefined){
            renderClientData(data);
            toggleEdit();
        }
    })

    btnSave.addEventListener('click', async ()=>{
        const form = document.getElementById('clientDetailsForm');
        const clientData = validateForm(form);
        if (clientData !== undefined){
            const data = await api.clients.updateClientDetailsRecord(clientData);
            if (data !== undefined){
                sessionStorage.setItem('clientData', JSON.stringify(data));
                renderClientData(data);
                toggleEdit();
            }
        }
    })

    function toggleEdit() {
        btnCancel.parentElement.classList.add('d-none');
        btnEdit.parentElement.classList.remove('d-none');
        formFields.forEach(el => {
            el.setAttribute('disabled', '')
        })
    }
}

function clientRemove(clientID){
    const msg = 'Are you sure you want to delete this client?';
    let newModal = modalConfirmDelete(msg, api.clients.deleteClient, ()=>{
        window.location.replace('/clients');
    });
    void newModal(clientID);
}

function renderClientData(clientData){
    for (let prop in clientData){
        document.getElementById(`${prop}`).value = clientData[`${prop}`];
    }
}
