import {api} from "./api.js";
import {modalClose, modalConfirmDelete, parsers, validateForm} from "./utils.js"
import {accountsModalObject} from "./accounts_modal.js";
import {periodModalObject} from "./period_modal.js";


const unvalidatedReportsList = document.getElementById('unvalidatedReportsList');
const clientID = document.getElementById('reportsList').dataset.clientId;
const reportConfigAccordion = document.getElementById('reportConfigAccordion');

let accountsModal
let periodModal
void setUp()

/**
 * Initial setup on loading
 * @return {Promise<void>}
 */
async function setUp(){
    document.querySelectorAll('#clientDetailsNav a')[3].classList.add('active');
    void await api.readMetadata();
    void loadFiles(clientID);
    periodModal = await periodModalObject({
        'modalTitle': 'Generate report',
        'clientID': clientID,
        'modalScopeFunc': async () => {
            let list = [{'id': 0, 'description': 'All reports'}];
            const clientReports = await api.clients.readClientReportsList(clientID);
            if (clientReports !== undefined){
                const parsedData = clientReports.map(el => {
                    const {id, 'file_name': fileName} = el;
                    return {'id': id, 'description': fileName}
                });
                list = parsedData.length === 1 ? parsedData : list.concat(parsedData);
            }
            return list
        }
    });
    assignListeners();
    setUpAddReportModal();

    ///stuck here
}

/**
 * Set up the addReportModal's dropdown menus to reflect the MetaData
 */
function setUpAddReportModal(){
    // Sets the global parameters of the addReportModal

    const {skipColumns} = JSON.parse(sessionStorage.getItem('configData'));
    const skipColumnsSelect = document.getElementById('newReportSkipColumns');
    skipColumnsSelect.replaceChildren(...skipColumns.map(el=>{
        let opt = document.createElement('option');
        let {id, 'skip_columns': skipColumns} = el;
        opt.value = id;
        opt.textContent = skipColumns;
        return opt;
    }));
}

/**
 * Assign overall listeners to the web page. Set's also listeners for pre-rendered report configs
 */
function assignListeners(){
    reportConfigAccordion.querySelectorAll('.accordion-item').forEach(el => addListenersReportConfig(el));
    document.getElementById('newReportForm').addEventListener('submit', ev => reportAdd(ev));
    document.getElementById('btnGenerateReports').addEventListener('click', () => {
        periodModal(console.log)
    });
}

// REPORT FILES
/**
 * Loads and renders the list of generated reports that are available for download
 * @param clientID {number|string} ID of the Client for which to render the report files
 * @return {Promise<void>}
 */
async function loadFiles(clientID){
    const reportFilesData = await api.clients.readClientReportFiles(clientID);
    if (reportFilesData !== undefined){
        const parsedReportsData = parsers.parseClientReportFiles(reportFilesData);
        unvalidatedReportsList.replaceChildren(...parsedReportsData.map(data => {
            const {reportID, period, fileName, reportType} = data;
            const item = document.getElementById('listItem').content.cloneNode(true);
            const a = item.querySelector('a')
            a.setAttribute('href', `/reports/download/billing/file/${reportID}/`);
            const spans = a.querySelectorAll('span');
            spans[0].textContent = `${period} => ${fileName}`;
            if (reportType === 6){
                spans[1].classList.remove('d-none');
            }
            return item;
        }))
    }
}

// REPORT CONFIGURATIONS
/**
 * Assigns listeners to all buttons and links for a report accordion
 * @param el {HTMLElement} report config accordion element
 */
function addListenersReportConfig(el){
        const inactiveSpan = el.querySelectorAll('.accordion-header span')[2];
        const accordionBody = el.querySelector('div.accordion-body');
        const reportID = accordionBody.querySelector('input').value;
        const inputs = Array.from(accordionBody.querySelectorAll('input, select')).slice(1);

        const configButtonGroup = accordionBody.querySelectorAll('button');
        configButtonGroup[0].addEventListener('click', () => {
            [0, 2].forEach(i => toggleVisibility(configButtonGroup[i].parentElement));
            inputs.forEach(el => el.disabled = true);
            void reportSaveDetails(reportID);
        });
        configButtonGroup[1].addEventListener('click', () => {
            [1, 2].forEach(i => toggleVisibility(configButtonGroup[i].parentElement));
            inputs.forEach(el => el.disabled = true);
            void reportDiscardChanges(reportID);
        });
        configButtonGroup[3].addEventListener('click', () => {
            [0, 3].forEach(i => toggleVisibility(configButtonGroup[i].parentElement));
            inputs.forEach(el => el.disabled = false);
        });
        configButtonGroup[4].addEventListener('click', () => {
            void reportAssignAccounts(reportID);
        });

        const configActionButtons = accordionBody.querySelectorAll('li a');
        configActionButtons[0].addEventListener('click', ev => {
            ev.preventDefault();
            [0, 1].forEach(i => toggleVisibility(configActionButtons[i]));
            [3, 4].forEach(i => {
                configButtonGroup[i].disabled = false;
                configButtonGroup[i].classList.add('btn-outline-primary');
                configButtonGroup[i].classList.remove('btn-outline-secondary');
            });
            configActionButtons[2].classList.toggle('disabled');
            inactiveSpan.classList.toggle('d-none');
            void reportSetActive(reportID);
        });
        configActionButtons[1].addEventListener('click', ev => {
            ev.preventDefault();
            [0, 1].forEach(i => toggleVisibility(configActionButtons[i]));
            [3, 4].forEach(i => {
                configButtonGroup[i].disabled = true;
                configButtonGroup[i].classList.remove('btn-outline-primary');
                configButtonGroup[i].classList.add('btn-outline-secondary');
            });
            configActionButtons[2].classList.toggle('disabled');
            inactiveSpan.classList.toggle('d-none');
            void reportSetActive(reportID, false);
        });
        configActionButtons[2].addEventListener('click', ev => {
            ev.preventDefault();
            reportRemove(reportID);
        });

        function toggleVisibility(el){
            el.classList.toggle('d-none')
        }
}

/**
 * Reads the data from the addReportModal, validates it, renders new element and adds it to the reports list
 * @param ev {Event} submit event of addReportModal
 * @return {Promise<void>}
 */
async function reportAdd(ev){
    ev.preventDefault();
    let formData = validateForm(ev.currentTarget);
    if (formData !== undefined){
        formData['client'] = clientID;
        const reportData = await api.reports.createReport(formData);
        if (reportData !== undefined){
            const parsedData = parsers.parseReportData(reportData);
            reportStoreDetails(parsedData);
            const newReportConfig = renderReport(parsedData);
            reportConfigAccordion.insertBefore(newReportConfig, reportConfigAccordion.firstChild);
            modalClose('addReportModal');
        }
    }
}

/**
 * Assigns Accounts to a given Report. Gets the IDs of already assigned accounts, launches the assignAccount modal and
 * on submit calls back a function to render the accounts list items and add them to the reportAccountsList element.
 * (updates the DB)
 * @param reportID {number|string} ID of the report to which accounts need to be assigned
 * @return {Promise<void>}
 */
async function reportAssignAccounts(reportID){
    const reportAccountsList = document.getElementById(`${reportID}reportAccountsList`);
    const assignedAccounts = Array.from(reportAccountsList.querySelectorAll('div.list-group-item'))
        .map(el => Number(el.dataset.accountId));
    accountsModal = accountsModalObject({
        'clientID': clientID,
        'reportID': reportID,
        'modalTitle': `Select accounts to assign to report ${reportID}`,
        'preselectedIDs': assignedAccounts
    });
    accountsModal(async (selectedItems) => {
        const {accountsList} = selectedItems;
        const requestData = {
            'reportID': reportID,
            'accountsList': {'vendors': accountsList}
        }
        const response = await api.reports.updateReportAccountsList(requestData)
        if (response !== undefined){
            const listItems = renderReportListItems(response);
            reportAccountsList.replaceChildren(...listItems);
        }
    });
}

/**
 * Discards any changes made while editing report details and renders the current state of the Report details.
 * @param reportID {number|string} ID of the report for which was being edited.
 */
function reportDiscardChanges(reportID){
    let data = JSON.parse(sessionStorage.getItem(`reportDetails${reportID}`));
    if (data === undefined){
        const result = api.reports.readReportDetails(reportID);
        data = parsers.parseReportData(result);
    }
    if (data !== undefined){
        const reportAccordion = document.getElementById(`${reportID}reportAccordionItem`)
        reportSetValues(reportAccordion, data);
    }
}

/**
 * Deletes a report for a given Client and removes it from the DOM (updates the DB)
 * @param reportID {number|string} ID of the report to be deleted
 */
function reportRemove(reportID){
    const msg = 'Are you sure you want to delete this report?';
    let newModal = modalConfirmDelete(msg, api.reports.deleteReport, () => {
        document.getElementById(`${reportID}reportAccordionItem`).remove();
        sessionStorage.removeItem(`reportDetails${reportID}`);
    });
    void newModal(reportID);
}

/**
 * Saves changes made to Report details (updates the DB)
 * @param reportID {number|string} ID of Report which to update
 * @return {Promise<void>}
 */
async function reportSaveDetails(reportID){
    const reportData = {
        'report_id': reportID,
        'file_name': document.getElementById(`${reportID}fileName`).value,
        'language': document.getElementById(`${reportID}language`).value,
        'skip_columns': document.getElementById(`${reportID}skipColumns`).value,
        'include_details': document.getElementById(`${reportID}includeDetails`).checked,
        'show_pids': document.getElementById(`${reportID}showPIDs`).checked
    };
    const result = await api.reports.updateReportDetails(reportData);
    if (result !== undefined){
        const parsedData = parsers.parseReportData(result);
        reportStoreDetails(parsedData);
        const reportAccordion = document.getElementById(`${reportID}reportAccordionItem`);
        reportSetValues(reportAccordion, parsedData);
    }
}

/**
 * Updates the is_active status of a Report (updates the DB)
 * @param reportID {number|string} ID of Report which to update
 * @param setActive  {boolean} the bool value to set to is_active
 * @return {Promise<void>}
 */
async function reportSetActive(reportID, setActive=true){
    const reportData = {
        'report_id': reportID,
        'is_active': setActive
    }
    void api.reports.updateReportDetails(reportData);
}

/**
 * Updates the reportAccordion item to set the details for a Report
 * @param reportAccordion {Element} DOM element to update
 * @param reportData {{fileName, clientID, reportID, skipColumns, language, isActive, includeDetails, showPIDs, vendorsList}}
 */
function reportSetValues(reportAccordion, reportData){
    const {fileName} = reportData;

    // Set heading
    reportAccordion.querySelector('span').textContent = fileName;

    // Set details
    const inputs = reportAccordion.querySelectorAll('input, select');
    inputs.forEach(el => {
        const elName = el.dataset.id;
        el.disabled = true;
        if (el.getAttribute('type') === 'checkbox'){
            el.checked = reportData[elName];
        } else {
            el.value = reportData[elName];
        }
    });
}

/**
 * Stores the Report details in the session storage
 * @param parsedData {{fileName, clientID, reportID, skipColumns, language, isActive, includeDetails, showPIDs, vendorsList}}
 */
function reportStoreDetails(parsedData){
    const {reportID} = parsedData;
    sessionStorage.setItem(`reportDetails${reportID}`, JSON.stringify(parsedData));
}

/**
 * Renders and returns a report accordion element given reportData
 * @param reportData {{fileName, clientID, reportID, skipColumns, language, isActive, includeDetails, showPIDs, vendorsList}}
 * @return {Node} element to be rendered to the DOM
 */
function renderReport(reportData){
    const {reportID} = reportData;
    const inactiveTag = document.getElementById('inactiveTag').content.cloneNode(true);
    const item = document.getElementById('reportAccordionItem').content.cloneNode(true);

    // Set heading IDs & attributes
    const accordionItem = item.querySelector('.accordion-item');
    accordionItem.id = `${reportID}reportAccordionItem`;
    const accordionHeader = item.querySelector('.accordion-header');
    accordionHeader.id = `${reportID}heading`;
    const accordionButton = item.querySelector('button');
    accordionButton.setAttribute('data-bs-target', `#${reportID}collapse`);
    accordionButton.appendChild(inactiveTag);
    item.querySelector('#reportAccountsList').id = `${reportID}reportAccountsList`;

    // Set details' IDs & attributes
    const accordionCollapse = item.querySelector('.accordion-collapse');
    accordionCollapse.id = `${reportID}collapse`;
    const inputs = accordionCollapse.querySelectorAll('div.form-floating input, div.form-floating select, div.form-check input');
    const labels = accordionCollapse.querySelectorAll('div.form-floating label, div.form-check label');
    inputs.forEach((el, i) => {
        let elName = el.getAttribute('data-id');
        el.id = `${reportID}${elName}`;
        labels[i].setAttribute('for', `${reportID}${elName}`);
    });

    // Set dropdown menus of Report details
    const {skipColumns, reportLanguages} = JSON.parse(sessionStorage.getItem('configData'));
    accordionCollapse.querySelector('select[data-id="language"]')
        .replaceChildren(...reportLanguages.map(el => {
            const {'id': optionID, 'language': optionText} = el;
            let opt = document.createElement('option');
            opt.value = optionID;
            opt.textContent = optionText;
            return opt;
        }));
    accordionCollapse.querySelector('select[data-id="skipColumns"]')
        .replaceChildren(...skipColumns.map(el => {
            const {'id': optionID, 'skip_columns': optionText} = el;
            let opt = document.createElement('option');
            opt.value = optionID
            opt.textContent = optionText;
            return opt;
        }));

    // Add order listeners
    reportSetValues(item, reportData);
    addListenersReportConfig(item);
    return item;
}

/**
 * Renders and returns a reportAccountList item given listItemData
 * @param listItemsData {{'vendor_id', 'description'}[]} Accounts data
 * @return {Node[]}
 */
function renderReportListItems(listItemsData){
    return listItemsData.map(el => {
       const {'vendor_id': accountID, 'description': accountDescription} = el;
       let item = document.getElementById('accountListItem').content.cloneNode(true);
       item.querySelector('div').setAttribute('data-account-id', accountID);
       const spans = item.querySelectorAll('span');
       spans[0].textContent = accountID;
       spans[1].textContent = accountDescription;
       return item;
    });
}