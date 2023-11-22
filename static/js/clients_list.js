import {api} from "./api.js";
import {cleanModalForm, validateForm} from "./utils.js";

const searchBar = document.getElementById('clientsListSearch');
const clientListRowTemplate = document.getElementById('clientListRowTemplate');
void setUp();

async function setUp(){
    sessionStorage.clear();
    void await api.readMetadata();
    setUpModal();
    assignListeners();
}

function setUpModal(){
    const {industries, countries} = JSON.parse(sessionStorage.getItem('configData'));
    const industrySelect = document.getElementById('industrySelect');
    industrySelect.replaceChildren(...industries.map(el=>{
        let opt = document.createElement('option');
        let {id, industry} = el;
        opt.value = id;
        opt.textContent = industry;
        return opt;
    }));
    industrySelect.value='';
    const countrySelect = document.getElementById('countrySelect');
    countrySelect.replaceChildren(...countries.map(el=>{
        let opt = document.createElement('option');
        let {id, country} = el;
        opt.value = id;
        opt.textContent = country;
        return opt;
    }));
    countrySelect.value='';
}

function assignListeners(){
    document.getElementById('clientSearchForm').addEventListener('submit', async (ev)=>{
        ev.preventDefault();
        if (searchBar.value !== ''){
            const searchParams = {'search': searchBar.value};
            const data = await api.clients.readClientsList(searchParams);
            if (data !== undefined){
                updateClientList(data);
            }
        } else {
            location.reload()
        }
    })
    document.getElementById('clientForm').addEventListener('submit', (ev)=>clientAdd(ev));
    document.addEventListener('show.bs.modal', (ev) => cleanModalForm(ev.target));
}

function  updateClientList(data){

    const tableRows = data.map(el=>{
        const {client_id: clientID, legal_name: legalName, reporting_name: reportingName} = el;
        const row = document.getElementById('clientListRowTemplate').content.cloneNode(true);
        row.querySelector('th').textContent = clientID;
        const clientName = row.querySelector('a');
        clientName.textContent = reportingName;
        clientName.href = `${clientID}/details`;
        row.querySelectorAll('td')[1].textContent = legalName;
        return row;
    })
    document.querySelector('tbody').replaceChildren(...tableRows);
    clientListRowTemplate.classList.add('d-none');
}

async function clientAdd(ev){
    // Add new order to the contract

    ev.preventDefault();
    let data = validateForm(ev.currentTarget);
    if (data !== undefined){
        const clientData = await api.clients.createClient(data);
        if (clientData !== undefined){
            const {'client_id': clientID} = clientData;
            window.location.href = `${clientID}/details`;
        }
    }
}