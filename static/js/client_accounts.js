import {api} from "./api.js";
import {modalClose, modalShow, hideElement, parsers} from "./utils.js";
import {servicesModalObject} from "./services_modal.js";
import {accountsModalObject} from "./accounts_modal.js";
import {periodModalObject} from "./period_modal.js";

// Set const for DOM elements
const accountsList = document.getElementById('accountsList');
const accountDetails = document.getElementById('accountDetails');
const accountDetailsTemplate = document.getElementById('accountDetailsTemplate');

let servicesModal;
let accountsModal;
let periodModal;
void setUp();

async function setUp(){
    // Set-up
    sessionStorage.clear();
    void await api.readMetadata();
    document.querySelectorAll('#clientDetailsNav a')[2].classList.add('active');
    const clientID = accountsList.dataset.clientId;
    accountsModal = accountsModalObject({
        'clientID': clientID,
        'modalTitle': `Assign accounts to Client ${clientID}`
    });
    servicesModal = servicesModalObject();

    // Assign listeners
    document.getElementById('btnAddAccount').addEventListener('click', () => {
        accountsModal(assignAccounts)
    });
    accountsListListeners();
}


// Accounts list

function accountsListListeners(){
    // Set the event listeners for the buttons on the accounts list.

    // List items -> trigger showAccountDetails
    accountsList.querySelectorAll('div a.list-group-item').forEach(btn => {
        btn.addEventListener('click', (ev) => {
            ev.preventDefault();
            const accountID = ev.target.closest('div').dataset.accountId;
            void showAccountDetails(accountID);
        });
    });

    // List items menu -> action on Activate, Deactivate, Remove
    accountsList.querySelectorAll('div ul').forEach(ul=>{
        const buttons = ul.querySelectorAll('a');
        buttons[0].addEventListener('click', async (ev) => void accountCalculateUsage(ev));
        buttons[1].addEventListener('click', async (ev) => {
            ev.preventDefault();
            const accountID = ev.target.closest('div').dataset.accountId;
            void updateAccountSetActive(accountID, true)
            toggleAccountDetailsButtons(true)
        });
        buttons[2].addEventListener('click', async (ev) => {
            ev.preventDefault();
            const accountID = ev.target.closest('div').dataset.accountId;
            void updateAccountSetActive(accountID, false);
            toggleAccountDetailsButtons(false)
        });
        buttons[3].addEventListener('click', async (ev) => {
            ev.preventDefault();
            const accountID = ev.target.closest('div').dataset.accountId;
            void removeAccount(accountID);
        });
    });
}

async function assignAccounts(data){
    // Assigns a list of accounts to a new client.
    // Stores the result into the sessionStorage.
    // data: {clientID, accountsList}

    let accountsData = await api.accounts.updateAccountOwner(data);
    if (accountsData !== undefined){
        accountsData = parsers.parseAccountDetails(accountsData);
        accountsData.forEach(el => storeAccountDetails(el))

        const accountsListItems = renderAccounts(accountsData);
        accountsList.replaceChildren(...accountsListItems);
        accountsListListeners();
    }
}

async function accountCalculateUsage(ev){
    ev.preventDefault();
    const listItem = ev.target.closest('div');
    const accountID = listItem.dataset.accountId;
    periodModal = await periodModalObject({
        'modalTitle': 'Calculate usage',
        'accountID': accountID,
        'modalScopeFunc': () => [{'id': accountID, 'description': `Account ${accountID}`}],
        'programScope': 'usage'
    });
    await periodModal(async () => {
        const response = await api.accounts.readAccountDetails(accountID);
        if (response !== undefined ){
            const accountData = parsers.parseAccountDetails(response);
            updateAccountListItem(listItem, accountData);
        }
    });
}

async function removeAccount(accountID){
    // Re-assign an account to clientID 0
    // Remove the item from the accountsList
    // Remove the details tab if it was showing that account

    // Re-assigns account to clientID 0
    const result = await api.accounts.updateAccountOwner({'clientID': 0, 'accountsList': [accountID]})
    if (result !== undefined){
        document.getElementById(`accountListItem${accountID}`).remove();
        sessionStorage.removeItem(`account${accountID}`);
    }

    // Remove the Account Details section
    const accountOnDisplay = accountDetails.querySelector('#accountID');
    if (accountOnDisplay && accountOnDisplay.value === accountID){
        accountDetails.replaceChildren();
    }
}

async function updateAccountSetActive(accountID, isActive=true){
    // Updates the account is_active status
    // Toggles the status of the buttons in the Account Details section if section is visible with this account
    // accountID: account number
    // isActive: bool

    if (accountID !== undefined){
        let accountData = await api.accounts.updateAccountRecord({accountID, isActive});
        if (accountData !== undefined){
            accountData = parsers.parseAccountDetails(accountData);
            sessionStorage.setItem(`account${accountData.accountID}`, JSON.stringify(accountData));
            const accountItem = document.getElementById(`accountListItem${accountID}`);
            updateAccountListItem(accountItem, accountData);
        }
    }
}

function updateAccountListItem(accountItem, accountData){
    // Updates the description, Active/Inactive/Unreconciled status of an account list item.
    // Updates the menu to set Activate/Deactivate.
    // accountItem: DOM element to update
    // accountData: {clientID, accountID, description, itecoName, isActive, isReconciled}

    const {accountID, description, isActive, isReconciled} = accountData;

    // Update tags
    const spans = accountItem.querySelectorAll('span');
    spans[0].textContent = accountID
    spans[1].textContent = description;
    hideElement(spans[2], isActive);
    hideElement(spans[3], isReconciled);

    // Update menu
    const buttons = accountItem.querySelectorAll('ul li a');
    hideElement(buttons[1], isActive);
    hideElement(buttons[2], !isActive);
}

function renderAccounts(accountsData){
    // Renders DOM elements for #accountsList
    // accountsData: [{clientID, accountID, description, itecoName, isActive, isReconciled}]


    return accountsData.map(data=>{
        const {accountID} = data;
        const item = document.getElementById('accountListTemplate').content.cloneNode(true);

        const listItem = item.querySelector('div');
        listItem.id = `accountListItem${accountID}`;
        listItem.setAttribute('data-account-id', accountID)

        const inactiveTag = document.getElementById('inactiveTag').content.cloneNode(true);
        item.querySelector('div a h6').appendChild(inactiveTag);

        const unreconciledTag = document.getElementById('unreconciledTagTemplate').content.cloneNode(true);
        item.querySelector('div a h6').appendChild(unreconciledTag);

        updateAccountListItem(listItem, data);
        return item;
    });
}


// Account details

function accountDetailsListeners(){
    // Sets the listeners for the account details section.

    const accountID = accountDetails.querySelector('#accountID').value;

    accountDetails.querySelector('#btnEdit').addEventListener('click', editAccountDetails);
    accountDetails.querySelector('#btnCancel').addEventListener('click', () => cancelEditAccountDetails(accountID));
    accountDetails.querySelector('#btnSave').addEventListener('click', () => saveAccountDetailsChanges(accountID));
    accountDetails.querySelector('#btnAddServices').addEventListener('click', () => accountAddServices(accountID));
    accountDetails.querySelector('#btnRemoveServices').addEventListener('click', () => accountRemoveServices(accountID));
    accountDetails.querySelector('#btnCopyFrom').addEventListener('click', (ev) => {
        ev.preventDefault();
        void copyServicesFromModal(accountID)
    });
}

async function showAccountDetails(accountID){
    // Displays the Account Details section.
    // accountID: account to read details for

    // Render account details and display them
    const accountData = await getAccountDetails(accountID);
    accountDetails.replaceChildren(renderAccountDetails(accountData));
    accountDetailsListeners()

    // Get servicesData from API, render services list and display them
    let servicesData = await api.accounts.readAccountServices(accountID);
    if (servicesData !== undefined){
        servicesData = parsers.parseClientServices(servicesData);
        accountDetails.querySelector('.list-group').replaceChildren(...renderAccountServices(servicesData));
    }
}

function editAccountDetails(){
    accountDetails.querySelector('#accountDescription').disabled = false;
    document.getElementById('accountDetailsButtons').querySelectorAll('button').forEach((btn, i) => {
        if ([0, 1].includes(i)) {
            btn.classList.remove('d-none')
        } else {
            btn.classList.add('d-none')
        }
    });
}

async function cancelEditAccountDetails(accountID){
    // Reverts changes to Account Details to the latest stored data.

    const accountData = await getAccountDetails(accountID);
    const descrEl = accountDetails.querySelector('#accountDescription');
    descrEl.value = accountData.description;
    descrEl.disabled = true;

    accountDetails.querySelectorAll('#accountDetailsButtons button').forEach((btn, i) => {
        if ([0, 1].includes(i)) {
            btn.classList.add('d-none');
        } else {
            btn.classList.remove('d-none');
        }
    });
}

async function saveAccountDetailsChanges(accountID){
    // Saves changes to Account Details and stores them in session storage.

    const description = accountDetails.querySelector('#accountDescription').value;
    if (description !== undefined){
        let accountData = await api.accounts.updateAccountRecord({accountID, description});
        if (accountData !== undefined){
            accountData = parsers.parseAccountDetails(accountData);
            storeAccountDetails(accountData);
            const currentListItem = document.getElementById(`accountListItem${accountID}`);
            const newListItem = renderAccounts([accountData]);
            currentListItem.parentNode.replaceChild(newListItem[0], currentListItem);

            accountDetails.querySelector('#accountDescription').disabled = true;
            accountDetails.querySelectorAll('#accountDetailsButtons button').forEach((btn, i) => {
            if ([0, 1].includes(i)) {
                btn.classList.add('d-none');
            } else {
                btn.classList.remove('d-none');
            }
        });
        }
    }
}

function renderAccountDetails(accountData){
    // Renders the DOM elements for the Account Details section.
    // accountData: {accountID, description, itecoName}

    const item = accountDetailsTemplate.content.cloneNode(true);
    const {accountID, description, itecoName} = accountData;
    item.getElementById('accountID').value = accountID;
    item.getElementById('accountDescription').value = description;
    item.getElementById('itecoName').value = itecoName;
    return item;
}

function toggleAccountDetailsButtons(isActive=true){
    // Enables and disables the buttons in the Account Details section

    const buttons = accountDetails.querySelectorAll('button');
    if (buttons !== undefined){
        buttons.forEach(btn => btn.disabled = !isActive);
        ['btn-outline-danger', 'btn-outline-success', 'btn-outline-primary',
        'btn-outline-danger', 'btn-outline-primary', 'btn-outline-primary'].forEach((el, i) => {
            buttons[i].classList.remove(isActive ? 'btn-outline-secondary' : el);
            buttons[i].classList.add(isActive ? el : 'btn-outline-secondary');
        });
    }

}


// Services
async function accountAddServices(accountID){
    // Add Services to Account

    const modalConfig = {
        'modalHeader': 'Select services to ADD to the account',
        'btnText': 'Add selected',
        'remove': false
    }
    let accountServicesData = await api.accounts.readAccountServices(accountID);
    if (accountServicesData !== undefined){
        accountServicesData = parsers.parseClientServices(accountServicesData);
        const assignedServices = accountServicesData.map(el=>el.serviceID);
        const services = JSON.parse(sessionStorage.getItem('services'))
            .filter(el=>!assignedServices.includes(el['service_id']))
            .map(el=>parsers.parseServiceProps(el))
        servicesModal(modalConfig, services, async (selectedItems)=>{
            let servicesData = await api.accounts.createAccountService({
                accountID,
                'ids': selectedItems
            });
            if (servicesData !== undefined){
                servicesData = parsers.parseClientServices(servicesData);
                accountDetails.querySelector('.list-group').replaceChildren(...renderAccountServices(servicesData));
            }
        })
    }
}

async function accountRemoveServices(accountID){
    // Remove services from Account

    const modalConfig = {
        'modalHeader': 'Select services to REMOVE to the account',
        'btnText': 'Remove selected',
        'remove': true
    }
    let accountServicesData = await api.accounts.readAccountServices(accountID);
    if (accountServicesData !== undefined){
        accountServicesData = parsers.parseClientServices(accountServicesData)
        const services = accountServicesData.map(el=>{
            const {accountID, ...rest} = el;
            return rest;
        })
        servicesModal(modalConfig, services, async (selectedItems)=>{
            let servicesData = await api.accounts.deleteAccountService({
                accountID,
                'ids': selectedItems
            });
            if (servicesData !== undefined){
                servicesData = parsers.parseClientServices(servicesData);
                accountDetails.querySelector('.list-group').replaceChildren(...renderAccountServices(servicesData));
            }
        })
    }
}

async function copyServicesFromModal(accountID){

    const clientID = accountsList.dataset.clientId;
    let accounts = await api.accounts.readAccountsList({'client_id': clientID});
    if (accounts !== undefined){
        accounts = parsers.parseAccountDetails(accounts);
        accounts = accounts.filter(el => el.accountID !== Number(accountID))
            .map(el => [el.accountID, `(${el.accountID}) ${el.description}`]);
        accounts.unshift(['', 'Select account to copy from']);
        const options = accounts.map(el => {
            const opt = document.createElement('option');
            opt.textContent = `${el[1]}`;
            opt.value = el[0];
            return opt;
        });
        const select = document.querySelector('#copyServicesModal select');
        select.replaceChildren(...options);
        modalShow('copyServicesModal');
        document.getElementById('copyServicesForm').addEventListener('submit', async (ev) => {
            ev.preventDefault();
            const selectedAccountID = document.querySelector('#copyServicesModal select').value;
            if (selectedAccountID !== ''){
                let servicesData = await api.accounts.duplicateServicesFrom({accountID, 'sourceAccountID': selectedAccountID});
                if (servicesData !== undefined){
                    servicesData = parsers.parseClientServices(servicesData);
                    accountDetails.querySelector('.list-group').replaceChildren(...renderAccountServices(servicesData));
                }
            }
            modalClose('copyServicesModal');
        }, {once: true});
    }
}

function renderAccountServices(servicesData){
    // Renders DOM elements for the Account Services rows for the Account Details sections.
    // Returns a list of DOM items.
    // serviceData: [{serviceID, description, serviceName, serviceType, filterOverride},]

    return servicesData.map(data => {
        const {serviceID, description, serviceName, serviceType, filterOverride} = data;
        const item = document.getElementById('accountServicesListItemTemplate').content.cloneNode(true);
        item.querySelector('div div').textContent = description;
        const spans = item.querySelectorAll('span');
        [serviceID, serviceName, serviceType].forEach((el, i) => spans[i].textContent = el);
        if (filterOverride !== undefined){
            spans[3].setAttribute('data-id', filterOverride);
            spans[3].textContent = `${filterOverride}`;
        }
        return item;
    });
}

// Other
async function getAccountDetails(accountID){
    // Reads account data from sessionStorage.
    // Alternatively reads data from API and stores result in session storage before returning it.
    // accountID: account to get details for.

    let data = JSON.parse(sessionStorage.getItem(`account${accountID}`));
    if (data === null){
        data = await api.accounts.readAccountDetails(accountID);
        if (data !== undefined){
            data = parsers.parseAccountDetails(data);
            sessionStorage.setItem(`account${accountID}`, JSON.stringify(data));
        }
    }
    return data;
}

function storeAccountDetails(parsedData){
    const {accountID} = parsedData;
    sessionStorage.setItem(`account${accountID}`, JSON.stringify(parsedData));
}