import {api} from "./api.js";
import {modalClose, modalShow} from "./utils.js";

/**
 * Sets-up an addAccountsModal
 * @param modalParams {{clientID, reportID, modalTitle, preselectedIDs}} params to customize the modal
 * @return {(function(*, *, function): void)|*} Function to be called on clicking the Assign accounts button.
 * The function receives the ids of the list items selected in the modal.
 */
export function accountsModalObject(modalParams) {

    // Set-up constants
    const modal = document.getElementById('modalAddAccount');
    const addAccountsList = modal.querySelector('#modalAddAccountsList');
    const accountsListTemplate = document.getElementById('accountModalListItemTemplate');
    const btnAssignAccounts = modal.querySelector('#btnAssignAccounts');
    const searchBox = modal.querySelector('#searchBox');
    const btnSearch = modal.querySelector('#searchGroup span');
    const unassignedCheck = modal.querySelector('#checkUnassigned');

    // Customize modal
    const {clientID, reportID, modalTitle, preselectedIDs} = modalParams;
    modal.querySelector('.modal-title').textContent = modalTitle !== undefined ? modalTitle : 'Accounts modal';
    if (reportID !== undefined){
        unassignedCheck.checked = false;
        modal.querySelector('#searchGroup').classList.add('d-none');
    } else {
        modal.querySelector('#searchGroup').classList.remove('d-none');
        unassignedCheck.checked = true;
    }

    // Set-up listeners
    modal.querySelectorAll('.modal-footer li a').forEach((btn, i)=>{
        btn.addEventListener('click', (ev)=>{
           ev.preventDefault();
           addAccountsList.querySelectorAll('input').forEach(el=>el.checked = i===0)
        });
    });
    btnSearch.addEventListener('click', accountSearch)
    searchBox.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') {void accountSearch()}
    });

    return async (callBack) => {
        let initialList;
        if (reportID!==undefined){
            initialList = await api.accounts.readAccountsList({'client_id': clientID});
        } else {
            initialList = await api.accounts.readAccountsList({'client_id': 0});
        }
        if (initialList !== undefined){
            updateAccountModalList(initialList, preselectedIDs);
            btnAssignAccounts.addEventListener('click', ()=>{
            const accountsList = Array.from(addAccountsList.querySelectorAll('input'))
                .filter(el=>el.checked)
                .map(el=>el.dataset.id);
            modalClose(modal.id);
            void callBack({clientID, accountsList});
        },{once: true})

            modalShow(modal.id)
        }
    }

    // Private functions
    async function accountSearch(){
        const searchValue = searchBox.value.trim()
        let searchParams = searchValue !== '' ? {'description' : searchBox.value} : {};
        if (unassignedCheck.checked){
            searchParams['client_id'] = 0;
        } else {
            searchParams['exclude_client_id'] = clientID;
        }

        const data = await api.accounts.readAccountsList(searchParams);
        if (data !== undefined){
            updateAccountModalList(data);
        }
    }
    function updateAccountModalList(data, preselectedIDs){
        const searchList = data.map(el=>{
            const {'vendor_id': accountID, description, 'is_reconciled': isReconciled, 'is_active': isActive} = el;
            const item = accountsListTemplate.content.cloneNode(true);
            const checkBox = item.querySelector('input');
            checkBox.setAttribute('data-id', accountID);
            const spans = item.querySelectorAll('span');
            spans[0].textContent = description
            spans[1].textContent = accountID;
            spans[2].textContent = isReconciled ? undefined : 'unreconciled';
            spans[3].textContent = isActive ? undefined : 'inactive';
            if (preselectedIDs !== undefined && preselectedIDs.includes(accountID)){
                checkBox.checked = true;
            }
            return item;
            });
        addAccountsList.replaceChildren(...searchList)
        addAccountsList.querySelectorAll('a').forEach(el=>{
            el.addEventListener('click', (ev) => {
                if (ev.target.tagName !== 'INPUT'){
                    ev.preventDefault();
                    const chkBox = ev.currentTarget.querySelector('input');
                    chkBox.checked = !chkBox.checked;
                }
            });
        });
    }
}