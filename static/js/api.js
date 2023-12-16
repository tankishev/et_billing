import { getCookie } from "./utils.js";

// Accounts

async function createAccountService(data){
    // Assigns Services to Accounts
    // data: {accountID, [ids]}

    const {accountID, ...rest} = data;
    const url = `/api/accounts/${accountID}/services/add/`;
    return await sendRecords(url, 'POST', rest);
}
async function readAccountDetails(accountID){
    // Returns the details for an account

    const url = `/api/accounts/${accountID}`;
    return await getRecords(url);
}
async function readAccountsList(searchParams) {
    // Search for accounts
    // searchParams: Search parameters

    const url = '/api/accounts/list';
    return await getWithSearch(url, searchParams);
}

async function readAccountServices(accountID){
    // Reads the Services for a given account
    // accountID: Account for which to return Services

    const url = `/api/accounts/${accountID}/services`;
    return await getRecords(url);
}

export async function updateAccountRecord(accountData){
    // Partial update of account records
    // data: {accountID, description, isActive}

    const {accountID, description, 'isActive': is_active} = accountData;
    const obj = {description, is_active};
    const data = Object.keys(obj).reduce((acc, key) => {
        if (obj[key] !== undefined){
            acc[key] = obj[key];
        }
        return acc;
    }, {});

    const url = `/api/accounts/${accountID}/`;
    return await sendRecords(url, 'PATCH', data);
}

async function updateAccountOwner(data){
    // Assigns a list of account_id to a given client_id
    // data: {clientID, accountsList}

    const {clientID, accountsList} = data
    const url = `/api/clients/${clientID}/accounts/`;
    return await sendRecords(url, 'POST', {'ids': accountsList});
}

async function duplicateServicesFrom(data){
    // Duplicate services from another account
    // data: {accountID, sourceAccountID}

    const {accountID, sourceAccountID} = data
    const url = `/api/accounts/${accountID}/duplicate-services`;
    return await getWithSearch(url, {'source_id': sourceAccountID});
}

async function deleteAccountService(data){
    // Removes services from account.
    // Cannot remove services that are included in orders (must be removed from Order before that)
    // data: {accountID, [selectedItems]}

    const {accountID, ...rest} = data;
    const url = `/api/accounts/${accountID}/services/remove/`;
    return await sendRecords(url, 'POST', rest);
}

// Clients

async function createClient(clientData){
    // Creates new client
    const url = '/api/clients/';
    return await sendRecords(url, 'POST', clientData);
}
async function readClientsList(searchParams){
    // Gets the Clients list
    // searchParams: {dictionary with parameters}

    const url = '/api/clients';
    return await getWithSearch(url, searchParams);
}

async function readClientDetails(clientID){
    // Get Client details

    const url = `/api/clients/${clientID}`;
    return await getRecords(url);
}

async function readClientIssues(clientID){
    // Returns issues with the Client set-up in ET-Billing

    const url = `/api/clients/${clientID}/issues`;
    return await getRecords(url);
}

async function readClientServices(clientID, searchParams){
    // Returns the Services associated with Accounts

    const url = `/api/clients/${clientID}/services`;
    return await getWithSearch(url, searchParams);
}

async function updateClientDetailsRecord(clientData){
    // Updates client records

    const { client_id: clientID, ...data } = clientData;
    const url = `/api/clients/${clientID}/`;
    return await sendRecords(url, 'PUT', data);
}

async function deleteClient(clientID){
    // Deletes the client record

    const url = `/api/clients/${clientID}`;
    return await deleteRecords(url);
}

// Contracts

async function createContract(contractData){
    // Creates a new Contract for the Client

    const url = '/api/contracts/';
    return await sendRecords(url, 'POST', contractData);
}

async function updateContract(contractData){
    // Updates Contract's data or status (active/inactive)

    const {'contract_id': contractID, ...data} = contractData;
    const url = `/api/contracts/${contractID}/`;
    return await sendRecords(url, 'PATCH', data);
}

async function deleteContract(contractId){
    // Deletes contract
    const url = `/api/contracts/${contractId}`;
    return await deleteRecords(url);
}

// Orders

async function createOrder(orderData){
    // Create new order and return results

    const url = '/api/orders/';
    return await sendRecords(url,'POST', orderData);
}

async function createDuplicateOrder(orderID){
    // Create new order and return results

    const url = `/api/orders/${orderID}/duplicate`;
    return await getRecords(url);
}

async function createOrderService(data){
    // Adds a service to a client's Order

    const {'order_id': orderID, ...rest} = data;
    const url = `/api/orders/${orderID}/services/add/`;
    return await sendRecords(url, 'POST', rest)
}

async function readOrdersList(contractID){
    // Get the orders list by contractID

    const url = `/api/contracts/${contractID}/orders`;
    return await getRecords(url);
}

async function readOrderPrices(orderID){
    // Gets the list of service prices for a given order

    const url = `/api/orders/${orderID}/prices`;
    return await getRecords(url);
}

async function readOrderServices(orderID){
    // Gets the list of accounts and services for given order

    const url = `/api/orders/${orderID}/services`;
    return await getRecords(url);
}

async function updateOrderDetails(orderData){
    // Partial update of order records

    const {'order_id': orderID, ...data} = orderData;
    const url = `/api/orders/${orderID}/`;
    return await sendRecords(url, 'PATCH', data);
}

async function updateOrderPrices(orderPriceData){
    // Partial update of order price data

    const {'id': orderPriceID} = orderPriceData;
    const url = `/api/order-service/${orderPriceID}/`;
    return await sendRecords(url, 'PATCH', orderPriceData);
}

async function deleteOrder(orderID){
    // Deletes an order record

    const url = `/api/orders/${orderID}/`;
    return await deleteRecords(url);
}

async function deleteOrderService(data){
    // Removes Services from an Order

    const {'order_id': orderID, ...rest} = data;
    const url = `/api/orders/${orderID}/services/remove/`;
    return await sendRecords(url, 'POST', rest)
}

async function readClientReportFiles(clientID){
    const url = `/api/clients/${clientID}/reports/files`;
    return await getRecords(url);
}

async function readClientReportsList(clientID){
    const url = `/api/clients/${clientID}/reports/list`
    return await getRecords(url);
}

// Reports

async function createReport(reportData){
    // Create new report

    const {'client': clientID} = reportData;
    const url = `/api/clients/${clientID}/reports/create/`;
    return await sendRecords(url,'POST', reportData);
}

async function readReportDetails(reportID){
    // Read details for a given Report

    const url = `/api/reports/${reportID}`
    return await getRecords(url);
}

async function updateReportAccountsList(reportData){
    // Updates the list of Accounts associated with a given Report

    const {reportID, accountsList} = reportData;
    const url = `/api/reports/${reportID}/assign-accounts/`;
    return await sendRecords(url, 'PUT', accountsList);
}

async function updateReportDetails(reportData){
    // Partial update of Report details

    const {'report_id': reportID, ...data} = reportData
    const url = `/api/reports/${reportID}/`
    return await sendRecords(url, 'PATCH', data);
}

async function deleteReport(reportID){
    // Deletes a report record

    const url = `/api/reports/${reportID}/`;
    return await deleteRecords(url);
}

async function generateClientReports(params){
    // Trigger generation of all reports for a given client

    const url = `/api/reports/generate/client/`;
    return await sendRecords(url, 'POST', params);
}

async function generateReports(params){
    // Trigger generation of a single report for a given client

    const url = `/api/reports/generate/report/`;
    return await sendRecords(url, 'POST', params);
}

// Utils

async function getWithSearch(endpoint, searchParams){

    let url = endpoint;
    if (searchParams !== undefined){
        const params = new URLSearchParams(searchParams);
        url = `${url}?${params}`;
    }
    return await getRecords(url);
}

export async function getRecords(endpoint){
    // Used for GET

    try {
        const response = await fetch(endpoint);
        if (response.ok){
            return await response.json();
        } else {
            void errorHandler(response, endpoint);
        }
    } catch (error) {
        console.error(error);
    }
}

async function sendRecords(endpoint, method, data){
    // Used for POST, PUT, PATCH
    const csrfToken = getCookie('csrftoken');
    try{
        const response = await fetch(endpoint, {
            method: method,
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (response.ok){
            return await response.json();
        } else {
            void errorHandler(response, endpoint, method);
        }
    } catch (error) {
        console.error(error);
    }
}

async function deleteRecords(endpoint){
    // Used for DELETE

    const csrfToken = getCookie('csrftoken');
    try{
        const response = await fetch(endpoint, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            }
        });
        if (response.ok) {
            return true;
        } else {
            void errorHandler(response, endpoint, 'DELETE');
        }
    } catch (error) {
        console.error(error);
    }
}

//Other

async function readMetadata(){
    // Get the metadata used for dropdown menus

    const url = '/api/metadata';
    const configData = await getRecords(url);
    const {services, ... rest} = configData;
    sessionStorage.setItem('configData', JSON.stringify(rest));
    sessionStorage.setItem('services', JSON.stringify(services));
}

async function readTaskStatus(taskID){
    // Reads the progress of a Celery task

    const url = `/api/tasks/${taskID}`;
    return await getRecords(url);
}

async function errorHandler(response, endpoint, method='GET'){
    let responseCopy = response.clone()
    console.log(await responseCopy.json())
    let error_message = `${method} to ${endpoint} failed.\nStatus: ${response.status} ${response.statusText}.`;
    const {message, ...rest} = await response.json();
    if (message !== undefined){
        error_message += `\nError: ${message}`;
    }
    if (rest !== undefined){
        error_message += `\nDRF errors:`;
        for (const [key, value] of Object.entries(rest)){
            error_message += `\n--> ${key}: ${value}`;
        }
    }
    window.alert( error_message);
    console.warn(error_message);
}

export const api = {
    accounts: {
        createAccountService,
        readAccountDetails,
        readAccountServices,
        readAccountsList,
        updateAccountOwner,
        updateAccountRecord,
        duplicateServicesFrom,
        deleteAccountService
    },
    clients: {
        createClient,
        readClientsList,
        readClientDetails,
        readClientIssues,
        readClientServices,
        readClientReportFiles,
        readClientReportsList,
        updateClientDetailsRecord,
        deleteClient
    },
    contracts: {
        createContract,
        updateContract,
        deleteContract
    },
    orders: {
        createOrder,
        createDuplicateOrder,
        createOrderService,
        readOrdersList,
        readOrderPrices,
        readOrderServices,
        updateOrderDetails,
        updateOrderPrices,
        deleteOrder,
        deleteOrderService
    },
    reports: {
        createReport,
        readReportDetails,
        updateReportAccountsList,
        updateReportDetails,
        deleteReport,
        generateClientReports,
        generateReports
    },
    readMetadata,
    readTaskStatus
}
