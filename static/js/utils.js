const debug = false;

export function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

export function hideElement(el, boolHide=true){
    if (boolHide) {
        el.classList.add('d-none');
    } else {
        el.classList.remove('d-none');
    }
}

// Modal related

/**
 * Shows a pop-up modal to confirm deletion of an object.
 * @param modalMessage message to display in the modal
 * @param callBack deletion function to call with an objectID
 * @param onSuccess function to call if deletion is successful
 * @type {(modalMessage: string, callBack: function, onSuccess: function) => function}
 * @return {function(elID: string|number): void} trigger function with param the ID to be passed to the callBack
 */
export function modalConfirmDelete(modalMessage, callBack, onSuccess){


    const myModal = document.getElementById('confirmAction');
    const bntConfirm = myModal.querySelector('#btnActionConfirm');
    bntConfirm.classList.remove('d-none');
    const alertText = myModal.querySelector('#confirmActionModalAlert');
    alertText.classList.add('d-none');
    myModal.querySelector('#confirmActionModalText').textContent = modalMessage;
    let modal = new bootstrap.Modal(myModal, {keyboard: false, backdrop: 'static'});

    return (elID)=>{
        bntConfirm.addEventListener('click', async ()=>{
            const success = await callBack(elID);
            if (success === true) {
                onSuccess();
                modal.hide();
            }
        }, {once: true});
        modal.show();
    }
}

/**
 * Closes a bootstrap modal
 * @param elementID {string} id of the element containing the modal
 */
export function modalClose(elementID){
    const myModalEl = document.getElementById(elementID);
    const modal = bootstrap.Modal.getInstance(myModalEl);
    modal.hide();
}

/**
 * Shows a boostrap modal
 * @param elementID {string} id of the element containing the modal
 */
export function modalShow(elementID){
    const myModal = document.getElementById(elementID);
    const modal = new bootstrap.Modal(myModal);
    modal.show()
}

export function cleanModalForm(targetModal){
    if (targetModal !== undefined && targetModal !== null){
        const form = targetModal.querySelector('form');
        if (form !== undefined && form !== null){
            form.querySelectorAll('input, select').forEach(el=>el.value='');
        }
    }
}

/**
 * Checks if all required fields are filled. Triggers CSS for missing required fields. Returns the form data.
 * @param form {HTMLFormElement} a target form to validate
 * @return {{[p: string]: undefined}} {field.dataset.id: field.value}[]
 */
export function validateForm(form){
    // Triggers CSS for missing required fields. If all required fields are populated returns an object:
    // {field.dataset.id: field.value, }

    const required = Array.from(form.querySelectorAll('[required]'))
    if (required.filter(el=>el.value==='').length !==0){
        form.classList.add('was-validated');
    } else {
        form.classList.remove('was-validated');
        let formData = Array.from(form.querySelectorAll('input, select'))
            .filter(el => el.value !== '')
            .map(el => {
                const value = el.getAttribute('type')==='checkbox' ? el.checked : el.value;
                return [el.dataset.id, value]
            });
        return Object.fromEntries(formData);
    }
}

// Parsers

function parseAccountDetails(accountsData){
    // Returns an object/ array of objects with the following structure:
    // {clientID, accountID, description, itecoName, isActive, isReconciled}

    let output;
    if (Array.isArray(accountsData)){
        output = accountsData.map(item => mapper(item)).sort((a, b)=>a.accountID - b.accountID);
    } else {
        output = mapper(accountsData);
    }
    if (debug) {console.log(output)}
    return output;

    function mapper(data){
        const {
            "vendor_id": accountID,
            'description': description,
            "is_reconciled": isReconciled,
            "iteco_name": itecoName,
            "is_active": isActive,
            "client": clientID
        } = data;
    return {clientID, accountID, description, itecoName, isActive, isReconciled};
    }
}

/**
 * Returns an Array object with parsed reportFileData
 * @param reportFilesData data for Client reports
 * @return {{period: string, fileName: string, filePath: string, accountsList: Array, reportType: number}[]}
 */
function parseClientReportFiles(reportFilesData){
    return reportFilesData.map(data => mapper(data));

    function mapper(data){
        const {'id': reportID, period, report, 'file': filePath, 'type_id': reportType} = data;
        const {'file_name': fileName, 'vendors': accountsList} = report;
        return {reportID, period, fileName, filePath, accountsList, reportType};
    }
}

function parseClientServices(clientServiceData){
    // Returns an object/ sorted array of objects with the following structure:
    // {accountServiceID, accountID, filterOverride, serviceID, serviceName, serviceType, sortingOrder, description}

    let output;
    if (Array.isArray(clientServiceData)){
        output = clientServiceData.map(item=>mapper(item)).sort((a, b)=>a['sortingOrder'] - b['sortingOrder']);
    } else {
        output = mapper(clientServiceData)
    }
    if (debug) {console.log(output)}
    return output;

    function mapper(data){
        let {
            'id': accountServiceID,
            'vendor': accountID,
            'service': service,
            'filter_override': filterOverride
        } = data;
        let serviceData = parseServiceProps(service)
        filterOverride = filterOverride === null ? undefined : filterOverride;
        return Object.assign({accountServiceID, accountID, filterOverride}, serviceData)
    }
}

function parseClientServicesPages(data){
    data['results'] = parseClientServices(data['results']);
    return data;
}

/**
 * Returns an object/ sorted array of objects
 * @param contractData - contractData object or an array of objects
 * @returns {{clientID: number, contractID: number, isActive: boolean, startDate: string, ordersList: Array}}
 */
function parseContractData(contractData){

    let output;
    if (Array.isArray(contractData)){
        output = contractData.map(item=>mapper(item)).sort((a, b)=>a['startDate'] - b['startDate']);
    } else {
        output = mapper(contractData)
    }
    if (debug) {console.log(output)}
    return output;

    function mapper(data){
        const {
            'contract_id': contractID,
            'orders': ordersData,
            'start_date': startDate,
            'is_active': isActive,
            'client': clientID
        } = data;
        const ordersList = parseOrderData(ordersData);
        return {clientID, contractID, startDate, isActive, ordersList};
    }
}

/**
 * Returns an object/ sorted array of objects
 * @param orderData - orderData object or an array of objects
 * @return {{orderID: number, startDate: string, endDate: string, description: string, ccyDescription: string,
 * ccyTypeID: number, pmtDescription: string, pmtTypeID: number, tuPrice: number, isActive: boolean}}
 */
function parseOrderData(orderData){
    let output;
    if (Array.isArray(orderData)){
        output = orderData.map(item=>mapper(item)).sort((a, b)=>a['startDate'] - b['startDate']);
    } else {
        output = mapper(orderData)
    }
    if (debug) {console.log(output)}
    return output;

    function mapper(data){
        const {
            "order_id": orderID,
            "start_date": startDate,
            "end_date": endDate,
            "description": description,
            "currency": ccyDescription,
            "ccy_type": ccyTypeID,
            "payment": pmtDescription,
            "payment_type": pmtTypeID,
            "tu_price": tuPrice,
            "is_active": isActive
        } = data;
        return {orderID, startDate, endDate, description, ccyDescription, ccyTypeID, pmtDescription, pmtTypeID, tuPrice, isActive};
    }

}

/**
 * Returns an object with service data
 * @param data orderServicesData
 * @return {{sortingOrder: {orderServiceId: number, serviceID: number, description: string, accounts: {accountID: number}[]}}}
 */
function parseOrderServices(data){
    // Returns an object with the following structure:
    // {sortingOrder, {orderServiceId, serviceID, description, accounts[accountID,]}

    if (data !== undefined){
        let accountServices = {};
        data.forEach(el => {
            const {'id': orderServiceId, 'service': item} = el;
            const {'service': service, 'vendor': accountID} = item;
            let serviceData = parseServiceProps(service);
            let {serviceType, serviceID, serviceName, sortingOrder} = serviceData;
            if (!(sortingOrder in accountServices)){
                serviceType = serviceType === null ? '' : serviceType;
                accountServices[serviceData.sortingOrder] = {
                    'description': `${serviceName} ${serviceType}`,
                    'accounts': [accountID],
                    orderServiceId,
                    serviceID
                };
            } else {
                accountServices[sortingOrder]['accounts'].push(accountID);
            }
        });
        if (debug) {console.log(accountServices)}
        return accountServices;
    }
}

/**
 * Returns an array with prices data objects
 * @param data - orderPriceData
 * @return {{orderPriceID, unitPrice, serviceID, serviceName, serviceType, sortingOrder, description}[]}
 */
function parseOrderPrices(data){
    // Receives an array and returns an object with the following structure:
    // {orderPriceID, unitPrice, serviceID, serviceName, serviceType, sortingOrder, description}

    if (Array.isArray(data)){
        return mapper(data).sort((a, b) => a['sortingOrder'] - b['sortingOrder']);
    }
    console.warn(`Expected Array, received ${typeof data} instead!`)

    function mapper(priceData){
        return priceData.map(el => {
            const {'id': orderPriceID, service, 'unit_price': unitPrice} = el;
            let serviceData = parseServiceProps(service);
            return Object.assign(serviceData, {orderPriceID, unitPrice})
        })
    }
}


function parseServiceProps(data){
    // Returns an object with the following structure:
    // {serviceID, serviceName, serviceType, sortingOrder, description}

    if (typeof data === "object"){
        const {
            'service_id': serviceID,
            'desc_en': description,
            'service_order':sortingOrder,
            'service': serviceName,
            'stype': serviceType
        } = data;
        const output = {serviceID, serviceName, serviceType, sortingOrder, description};
        if (debug) {console.log(output)}
        return output;
    }
    console.warn(`Expected Object, received ${typeof data} instead!`)
}

/**
 * Returns an object with Report data attributes
 * @param data reportData returned by the API call
 * @return {{fileName, clientID, reportID, skipColumns, language, isActive, includeDetails, showPIDs, vendorsList}}
 */
function parseReportData(data){
    if (typeof data === "object"){
        const {
            'id': reportID,
            'client': clientID,
            'file_name':fileName,
            'is_active': isActive,
            'include_details': includeDetails,
            'show_pids': showPIDs,
            'language':language,
            'skip_columns': skipColumns,
            'vendors': vendorsList,

        } = data;
        const output = {reportID, clientID, fileName, isActive, includeDetails, showPIDs, language, skipColumns, vendorsList};
        if (debug) {console.log(output)}
        return output;
    }
    console.warn(`Expected Object, received ${typeof data} instead!`)
}

export const parsers = {
    parseAccountDetails,
    parseClientReportFiles,
    parseClientServices,
    parseClientServicesPages,
    parseContractData,
    parseOrderData,
    parseOrderServices,
    parseOrderPrices,
    parseServiceProps,
    parseReportData
}

// Other

export function getPreviousPeriod() {
    const today = new Date();
    const previousMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    const year = previousMonth.getFullYear();
    const month = previousMonth.getMonth() + 1;
    const formattedMonth = month.toString().padStart(2, '0');

    return `${year}-${formattedMonth}`;
}
