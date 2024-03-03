import {
    modalClose,
    validateForm,
    modalConfirmDelete,
    cleanModalForm,
    parsers
} from "./utils.js";
import {api} from "./api.js";
import {servicesModalObject} from "./services_modal.js";

const contractsList = document.getElementById('contractsList');
const ordersList = document.getElementById('ordersList');
const ordersListAccordion = document.getElementById('ordersListAccordion');
const inactiveTag = document.getElementById('inactiveTag')
const clientID = contractsList.dataset.clientId;
let servicesModal;
let contractModal;
void setUp();

async function setUp(){
    sessionStorage.clear();
    document.querySelectorAll('#clientDetailsNav a')[1].classList.add('active');
    void await api.readMetadata();
    setUpNewOrderModal()
    addListeners();
    servicesModal = servicesModalObject(true);
}

function setUpNewOrderModal(){
    // Sets the global parameters of the newOrderModal modal

    const {ccyTypes, pmtTypes} = JSON.parse(sessionStorage.getItem('configData'));
    const currencySelect = document.getElementById('newOrderCurrency');
    currencySelect.replaceChildren(...ccyTypes.map(el=>{
        let opt = document.createElement('option');
        let {id, 'ccy_type': ccyType} = el;
        opt.value = id;
        opt.textContent = ccyType;
        return opt;
    }));
    currencySelect.value='';
    const selectPmtType = document.getElementById('newOrderPmtType');
    selectPmtType.replaceChildren(...pmtTypes.map(el=>{
        let opt = document.createElement('option');
        let {id, description} = el;
        opt.value = id;
        opt.textContent = description;
        return opt;
    }));
    selectPmtType.value='';
}

function addListeners(){
    // Add global listeners

    Array.from(contractsList.children).forEach(el => contractAddListeners(el));
    document.getElementById('orderForm').addEventListener('submit', (ev) => orderAdd(ev));
    document.getElementById('btnAddContract').addEventListener('click', addContract);
    document.addEventListener('show.bs.modal', (ev) => cleanModalForm(ev.target));
}

/**
 * Returns a modal object that can be reused for Contract create and edit
 * @return {(function({modalHeader: string, btnText: string}, function): void)|*}
 */
function contractModalObject(){
    const modalElement = document.getElementById('addContractModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    const heading = modalElement.querySelector('h5');
    const form = modalElement.querySelector('.modal-body form');
    const btnSubmit = modalElement.querySelector('.modal-footer button');

    return (modalConfig, callBack) => {
        const {modalHeader, btnText} = modalConfig;
        heading.textContent = modalHeader;
        btnSubmit.textContent = btnText;

        function validateAndSubmit(){
            form.addEventListener('submit',  (ev) => {
                ev.preventDefault();
                let formData = validateForm(form);
                if (formData !== undefined){
                    void callBack(formData);
                    modalElement.querySelector('#newContractStartDate').value = '';
                    modal.hide()
                } else {
                    validateAndSubmit();
                }
            }, {once: true});
        }

        validateAndSubmit();
        modal.show()
    }
}

// Contracts List

/**
 * Adds listeners to a contractsList element
 * @param el {HTMLElement} a contractsList element to add listeners to
 */
function contractAddListeners(el){
    const contractID = el.dataset.id;
    const heading = el.querySelector('h6');

    heading.addEventListener('click', (ev) => {
        ev.preventDefault();
        void renderOrdersList(contractID);
    });

    const aList = el.querySelectorAll('ul li a');
    aList[0].addEventListener('click', async (ev) => {
        ev.preventDefault();
        ev.target.classList.add('d-none')
        aList[1].classList.remove('d-none');
        const contractData = await contractSetActive(contractID);
        if (contractData !== undefined){
            heading.querySelector('span.badge').classList.add('d-none');
        }
    });
    aList[1].addEventListener('click', async (ev) => {
        ev.preventDefault();
        ev.target.classList.add('d-none')
        aList[0].classList.remove('d-none');
        const contractData = await contractSetActive(contractID, false);
        if (contractData !== undefined){
            heading.querySelector('span.badge').classList.remove('d-none');
        }
    });
    aList[2].addEventListener('click', (ev) => {
        ev.preventDefault();
        contractEdit(contractID);
    });
    aList[3].addEventListener('click', (ev) => {
        ev.preventDefault();
        contractRemove(el);
    });
}

/**
 * Sets the isActive status of a Contract
 * @param contractID {string|number} ID of the Contract
 * @param isActive {boolean} status to set
 * @return {Promise<{clientID: number, contractID: number, isActive: boolean, startDate: string, ordersList: Array}|Array>}
 */
async function contractSetActive(contractID, isActive=true){
    const contractData = await api.contracts.updateContract({'contract_id': contractID, 'is_active': isActive});
    if (contractData !== undefined){
        const parsedData = parsers.parseContractData(contractData);
        storeContractDetails(parsedData);
        if (!isActive){
            void await deactivateOrders()
        }
        return parsedData;
    }
    async function deactivateOrders(){
        const ordersList = await api.orders.readOrdersList(contractID);
        if (ordersList !== undefined){
            const parsedData = parsers.parseOrderData(ordersList);
            parsedData.map(el => el.orderID).forEach(orderID => {
                orderSetActiveStatus(orderID, false);
            })
        }
    }
}

/**
 * Creates a new contract based on the information from the addContractModal.
 * Renders the new Contract and adds it to the contractsList.
 * @return {Promise<void>}
 */
async function addContract(){
    contractModal = contractModalObject();
    const modalConfig = {
        'modalHeader': `Add contract for Client ${clientID}`,
        'btnText': 'Add contract'
    }

    contractModal(modalConfig, async (formData) => {
        formData['client'] = clientID;
        let newContractData = await api.contracts.createContract(formData);
        if (newContractData !== undefined){
            newContractData = parsers.parseContractData(newContractData);
            storeContractDetails(newContractData);
            const item = renderContract(newContractData);
            contractsList.insertBefore(item, contractsList.firstChild);
        }
    })
}

/**
 * Edits the date of the Contract. Updates the contractsList heading as well.
 * @param contractID {string|number} ID of contract to Edit
 */
function contractEdit(contractID){
    contractModal = contractModalObject();
    const modalConfig = {
        'modalHeader': `Contract ${contractID}: Edit date`,
        'btnText': 'Edit contract'
    }

    contractModal(modalConfig, async (formData) => {
        formData['contract_id'] = contractID;
        let contractData = await api.contracts.updateContract(formData);
        if (contractData !== undefined){
            contractData = parsers.parseContractData(contractData);
            storeContractDetails(contractData);
            const contractItem = `#contract${contractID} h6`;
            contractsList.querySelector(contractItem).childNodes[0]
                .textContent = `Contract ${contractID} / ${formData['start_date']}`;
        }
    })
}

/**
 * Deletes a Contract and removes its element from the contractsList
 * @param el {HTMLElement} the Contract element containing the contractID
 */
function contractRemove(el){
    const msg = 'Are you sure you want to delete this contract?';
    let newModal = modalConfirmDelete(msg, api.contracts.deleteContract, () => {
        el.remove();
        ordersList.classList.add('d-none');
    });
    void newModal(el.dataset.id);
}

// Orders
/**
 * Add new Order to a Contract
 * @param ev {Event} submit event from the addContractModal
 */
async function orderAdd(ev){
    ev.preventDefault();
    let formData = validateForm(ev.currentTarget);
    if (formData !== undefined){
        formData['contract'] = ordersList.dataset['contract_id'];
        const orderData = await api.orders.createOrder(formData);
        if (orderData !== undefined){
            const parsedData = parsers.parseOrderData(orderData);
            storeOrderDetails(parsedData);
            const newOrder = await renderOrder(parsedData);
            ordersListAccordion.insertBefore(newOrder, ordersListAccordion.firstChild);
            modalClose('addOrderModal');
        }
    }
}

/**
 * Discard changes to Order details and revert back to recorded values
 * @param orderID {string | number} ID of the order being edited
 */
function orderDiscardChanges(orderID){
    const data = JSON.parse(sessionStorage.getItem(`order${orderID}`));
    if (data !== undefined){
        const orderAccordion = document.getElementById(`${orderID}orderAccordion`)
        orderDetailsSetValues(orderAccordion, data);
    }
}

/**
 * Activate/Deactivate and Order and updates the orderAccordion
 * @param orderID {number|string} ID of order to update
 * @param isActive {boolean} status to set
 */
async function orderSetActiveStatus(orderID, isActive=true){
    const orderData = await api.orders.updateOrderDetails({'order_id': orderID, 'is_active': isActive});
    if (orderData !== undefined){
        const parsedData = parsers.parseOrderData(orderData);
        storeOrderDetails(parsedData);

        const accordion = document.getElementById(`${orderID}orderAccordion`);
        if (accordion !== null){
            orderSetButtonStatus(accordion, isActive);
            orderHeadingSetActiveStatus(accordion, isActive);
        }
    }
}

/**
 * Deletes and Order and removes it from the ordersList
 * @param orderID {number|string} ID of the Order to remove
 */
function orderRemove(orderID){
    const msg = 'Are you sure you want to delete this order?';
    let newModal = modalConfirmDelete(msg, api.orders.deleteOrder, () => {
        document.getElementById(`${orderID}orderAccordion`).remove();
        sessionStorage.removeItem(`order${orderID}`);
    });
    void newModal(orderID);
}

/**
 * Duplicates an Order
 * @param orderID {string|number} ID of order to duplicate
 * @return {Promise<void>}
 */
async function orderDuplicate(orderID){
    const orderData = await api.orders.createDuplicateOrder(orderID);
    if (orderData !== undefined){
        const parsedData = parsers.parseOrderData(orderData);
        storeOrderDetails(parsedData);
        const newOrder = await renderOrder(parsedData);
        ordersListAccordion.insertBefore(newOrder, ordersListAccordion.firstChild);
    }
}

/**
 * Enables the form fields to edit Order details
 * @param orderID {string|number} ID of the Order to edit
 */
function orderEditDetails(orderID){
    document.getElementById(`${orderID}startDate`).disabled = false;
    document.getElementById(`${orderID}endDate`).disabled = false;
    document.getElementById(`${orderID}tuPrice`).disabled = false;
    document.getElementById(`${orderID}pmtTypeID`).disabled = false;
    document.getElementById(`${orderID}ccyTypeID`).disabled = false;
    document.getElementById(`${orderID}description`).readOnly = false;
}

/**
 * Updates the Order details and sets the order fields to disabled
 * @param orderID {string|number} ID of the Order
 */
async function orderSaveDetails(orderID){
    const orderData = {
        'order_id': orderID,
        'start_date': document.getElementById(`${orderID}startDate`).value,
        'end_date': document.getElementById(`${orderID}endDate`).value,
        'tu_price': document.getElementById(`${orderID}tuPrice`).value,
        'payment_type': document.getElementById(`${orderID}pmtTypeID`).value,
        'ccy_type': document.getElementById(`${orderID}ccyTypeID`).value,
        'description': document.getElementById(`${orderID}description`).value
    };
    const result = await api.orders.updateOrderDetails(orderData);
    if (result !== undefined){
        const parsedData = parsers.parseOrderData(result);
        storeOrderDetails(parsedData);
        const orderAccordion = document.getElementById(`${orderID}orderAccordion`);
        orderDetailsSetValues(orderAccordion, parsedData);
    }
}

/**
 * Sets the inactiveTag on orderHeaders
 * @param orderAccordion {HTMLElement} ID of order to update
 * @param isActive {boolean} order status
 */
function orderHeadingSetActiveStatus(orderAccordion, isActive=true){
    const spans = orderAccordion.querySelectorAll('.accordion-button span');
    if (isActive){
        spans[1].classList.add('d-none');
    } else {
        spans[1].classList.remove('d-none');
    }
}

/**
 * Fills in the Order Details section of an accordion body
 * @param orderAccordion {HTMLElement} order accordion element
 * @param orderData {{orderID: number|string, startDate: string, endDate: string, description: string,
 * isActive: boolean}} parsed order details data
 */
function orderDetailsSetValues(orderAccordion, orderData){
    const {orderID, startDate, description, isActive} = orderData;

    // Set heading
    const spans = orderAccordion.querySelectorAll('.accordion-button span');
    spans[0].textContent = `${orderID} / ${startDate}`;
    spans[0].innerHTML += "&emsp;"
    orderHeadingSetActiveStatus(orderAccordion, isActive);

    // Set details
    orderAccordion.querySelector('textarea').value = description;
    const inputs = orderAccordion.querySelectorAll('div.form-floating input, div.form-floating select');
    inputs.forEach(el => {
       el.disabled = true;
       el.value = orderData[el.dataset.id]
    });
}

/**
 * Sets the CSS formatting of Order buttons depending on order isActive status
 * @param orderAccordion {HTMLElement} order element to update
 * @param isActive {boolean} Order isActive status
 */
function orderSetButtonStatus(orderAccordion, isActive){
    // Edit details buttons
    const buttons = Array.from(orderAccordion.querySelectorAll('button'))
        .filter((btn, i) => [3,4,7,8].includes(i));
    buttons.forEach((btn, i) => {
        ['btn-outline-primary', 'btn-outline-secondary', 'btn-outline-danger'].forEach(el=> {btn.classList.remove(el);});
        if(i > 0){btn.disabled = !isActive}
        if(i === 3){
            btn.classList.add(isActive?'btn-outline-danger':'btn-outline-secondary');
        } else {
            btn.classList.add(isActive?'btn-outline-primary':'btn-outline-secondary');
        }
    });

    // Menu items
    const menuButtons = orderAccordion.querySelectorAll('ul a');
    if (isActive){
        menuButtons[0].classList.add('d-none');
        menuButtons[1].classList.remove('d-none');
    } else {
        menuButtons[1].classList.add('d-none');
        menuButtons[0].classList.remove('d-none');
    }

    // Price edit buttons
    if (isActive){
        orderAccordion.querySelectorAll('div.tab-pane a.text-primary').forEach(el => el.classList.remove('d-none'));
    } else {
        orderAccordion.querySelectorAll('div.tab-pane a').forEach(el => el.classList.add('d-none'));
        orderAccordion.querySelectorAll('div.tab-pane input').forEach(el => el.disabled = true);
    }
}

// Services
/**
 * Launches the Add Service Modal. Adds selected services to the Order and renders the orderServices tab of the orderAccordion
 * @param orderID {string|number} ID of the order to add services to
 */
async function orderAddService(orderID){
    const modalConfig = {
        'modalHeader': 'Add services to order',
        'btnText': 'Add selected',
        'remove': false
    }
    const clientServicesData = await api.clients.readClientServices(clientID, {'exclude_assigned': true});
    if (clientServicesData !== undefined){
        const data = parsers.parseClientServicesPages(clientServicesData);
        servicesModal(modalConfig, data, async (selectedItems) => {
            const data = await api.orders.createOrderService({
                'order_id': orderID,
                'ids': selectedItems
            });
            if (data !== undefined){
                void orderUpdateServicePriceLists(orderID, data)
            }
        })
    }
}

/**
 * Launches the Remove Service Modal. Removes selected services to the Order and renders the orderServices tab of the orderAccordion
 * @param orderID {string|number} ID of the order to remove services from
 */
async function orderRemoveService(orderID) {
    const modalConfig = {
        'modalHeader': 'Remove service from order',
        'btnText': 'Remove selected',
        'remove': true
    }
    const clientServicesData = await api.clients.readClientServices(clientID, {'order_id': orderID});
    if (clientServicesData !== undefined){
        const data = parsers.parseClientServicesPages(clientServicesData);
        servicesModal(modalConfig, data, async (selectedItems) => {
            const data = await api.orders.deleteOrderService({
                'order_id': orderID,
                'ids': selectedItems
            });
            if (data !== undefined){
                void orderUpdateServicePriceLists(orderID, data)
            }
        })
    }
}

/**
 * Sets the services and prices tables of an Order post Service Add/Remove
 * @param orderID {number|string} ID of order to update
 * @param serviceData services data from API call
 * @return {Promise<void>}
 */
async function orderUpdateServicePriceLists(orderID, serviceData){
    const parsedData = parsers.parseOrderServices(serviceData);
    const services = renderOrderServicesItems(parsedData);
    document.getElementById(`${orderID}orderServices`).querySelector('.col')
        .children[1].replaceChildren(...services);
    const prices = await renderOrderPrices(orderID);
    document.getElementById(`${orderID}orderPrices`).replaceChildren(...prices)
}

// Rendering

/**
 * Renders and returns an element for the contractList
 * @param contractData {{contractID: string|number, startDate: string, isActive: boolean}}
 * @return {DocumentFragment} item to be added to the contractsList
 */
function renderContract(contractData){
    const {contractID, startDate, isActive} = contractData;
    const item = document.getElementById('contractTemplate').content.cloneNode(true);
    const div = item.querySelector('div');
    const i = isActive? 1 : 0;

    div.id = `contract${contractID}`;
    div.setAttribute('data-id', contractID);
    div.querySelector('h6').textContent = `Contract ${contractID} / ${startDate}`;
    div.querySelectorAll('ul li a')[i].classList.remove('d-none');
    contractAddListeners(div);

    return item;
}

/**
 * Renders the ordersList for a given Contract
 * @param contractID {number|string} ID of the contract for which to render the ordersList
 * @return {Promise<void>}
 */
async function renderOrdersList(contractID){
    // Hide ordersList and show loading modal
    ordersList.classList.add('d-none');
    const myModal = document.getElementById('loadingModal');
    let modal = new bootstrap.Modal(myModal, {keyboard: false, backdrop: 'static'});
    modal.show();

    // Add orders in the list
    ordersListAccordion.replaceChildren();
    const ordersListData = await api.orders.readOrdersList(contractID);
    if (ordersListData !== undefined){
        const parsedData = parsers.parseOrderData(ordersListData);
        for await (let data of parsedData){
            storeOrderDetails(data);
            const newOrder = await renderOrder(data);
            ordersListAccordion.appendChild(newOrder);
        }
    }

    // Show ordersList and hide the loading modal
    ordersList.dataset['contract_id'] = contractID;
    ordersList.classList.remove('d-none');
    bootstrap.Modal.getInstance(myModal).hide();
}

/**
 * Renders and returns an orderAccordion element for the ordersList
 * @param orderData {{orderID: number|string, startDate: string, endDate: string, description: string,
 * ccyDescription: string, ccyTypeID: number, pmtDescription: string, pmtTypeID: number, tuPrice: number,
 * isActive: boolean}} - oderData object
 * @return {DocumentFragment} - an element to be appended to ordersList
 */
async function renderOrder(orderData){
    // Renders an Order
    const {orderID, isActive} = orderData;
    const [prices, services] = await Promise.all([renderOrderPrices(orderID), renderOrderServices(orderID)])
    const item = document.getElementById('orderTemplate').content.cloneNode(true);

    // Set heading IDs & attributes
    const accordionItem = item.querySelector('.accordion-item');
    accordionItem.id = `${orderID}orderAccordion`;
    accordionItem.setAttribute('data-id', orderID);
    const accordionHeader = item.querySelector('.accordion-header');
    accordionHeader.id = `${orderID}heading`;
    const accordionButton = item.querySelector('button');
    accordionButton.id = `${orderID}headingButton`;
    accordionButton.setAttribute('data-bs-target', `#${orderID}collapse`);
    accordionButton.appendChild(inactiveTag.content.cloneNode(true))

    // Set details' IDs & attributes
    const accordionCollapse = item.querySelector('.accordion-collapse');
    accordionCollapse.id = `${orderID}collapse`;
    const labels = accordionCollapse.querySelectorAll('.accordion-body label');

    accordionCollapse.querySelector('.accordion-body textarea').id = `${orderID}description`;
    labels[0].setAttribute('for', `${orderID}description`);

    item.querySelector('#startDate').id = `${orderID}startDate`;
    labels[1].setAttribute('for', `${orderID}startDate`);

    item.querySelector('#endDate').id = `${orderID}endDate`;
    labels[2].setAttribute('for', `${orderID}endDate`);

    const orderPaymentType = item.querySelector('#paymentType');
    orderPaymentType.id = `${orderID}pmtTypeID`;
    labels[3].setAttribute('for', `${orderID}pmtTypeID`);

    const orderCcyType = item.querySelector('#ccyType');
    orderCcyType.id = `${orderID}ccyTypeID`;
    labels[4].setAttribute('for', `${orderID}ccyTypeID`);

    item.querySelector('#tuPrice').id = `${orderID}tuPrice`;
    labels[5].setAttribute('for', `${orderID}tuPrice`);

    // Set dropdown menus of Order Details
    const {pmtTypes, ccyTypes} = JSON.parse(sessionStorage.getItem('configData'));
    const [pmtOptions, ccyOptions] = [pmtTypes, ccyTypes].map(el => renderOptions(el));
    orderPaymentType.replaceChildren(...pmtOptions);
    orderCcyType.replaceChildren(...ccyOptions);

    // Render order services tab
    const btnOrderServicesTab = item.querySelector('#orderServicesTab');
    btnOrderServicesTab.setAttribute('data-bs-target', `#${orderID}orderServices`);
    const btnAddService = item.querySelector('#addService');
    btnAddService.id = `${orderID}addService`;
    const btnRemoveService = item.querySelector('#removeService');
    btnRemoveService.id = `${orderID}removeService`;
    item.querySelector('#orderServices .col').children[1].replaceChildren(...services);
    item.querySelector('#orderServices').id = `${orderID}orderServices`;

    // Render order prices tab
    const btnOrderPricesTab = item.querySelector('#orderPricesTab');
    btnOrderPricesTab.setAttribute('data-bs-target', `#${orderID}orderPrices`);
    item.querySelector('#orderPrices').id = `${orderID}orderPrices`;
    item.querySelector('#orderPricesList').replaceChildren(...prices);
    item.querySelector('#orderPricesList').id = `${orderID}orderPricesList`;

    // Fills in Order Details
    orderDetailsSetValues(accordionItem, orderData)
    orderSetButtonStatus(item, isActive);

    // Add order listeners
    const buttonsList = item.querySelectorAll('button');
    const editOrderGroup = buttonsList[4].parentNode;
    buttonsList[1].addEventListener('click', (ev) => {
        ev.target.parentNode.classList.add('d-none');
        editOrderGroup.classList.remove('d-none');
        void orderSaveDetails(orderID);
    });
    buttonsList[2].addEventListener('click', (ev) => {
        ev.target.parentNode.classList.add('d-none');
        editOrderGroup.classList.remove('d-none');
        void orderDiscardChanges(orderID);
    });
    buttonsList[4].addEventListener('click', () => {
        editOrderGroup.classList.add('d-none');
        buttonsList[1].parentNode.classList.remove('d-none');
        orderEditDetails(orderID)
    });
    const editOrderGroupLi = editOrderGroup.querySelectorAll('a');
    editOrderGroupLi[0].addEventListener('click', (ev) => {
        ev.preventDefault();
        // ev.target.classList.add('d-none')
        // editOrderGroupLi[1].classList.remove('d-none');
        void orderSetActiveStatus(orderID);
    });
    editOrderGroupLi[1].addEventListener('click', (ev) => {
        ev.preventDefault();
        // ev.target.classList.add('d-none')
        // editOrderGroupLi[0].classList.remove('d-none')
        void orderSetActiveStatus(orderID, false);
    });
    editOrderGroupLi[2].addEventListener('click', (ev) => {
        ev.preventDefault();
        orderDuplicate(orderID);
    });
    editOrderGroupLi[3].addEventListener('click', (ev) => {
        ev.preventDefault();
        void orderRemove(orderID);
    });
    buttonsList[7].addEventListener('click', () => orderAddService(orderID));
    buttonsList[8].addEventListener('click', () => orderRemoveService(orderID));

    return item;

    function renderOptions(data){
        return data.map(el => {
            const {'id' : optionID, 'ccy_type': ccyType, 'description': pmtType} = el;
            const description = ccyType !== undefined ? ccyType : pmtType;
            let opt = document.createElement('option');
            opt.value = optionID;
            opt.textContent = description;
            return opt;
        })
    }
}

/**
 * Renders a list of items for the orderPricesList
 * @param orderID {string|number} ID for which to generate the service prices
 * @return {Promise<Node[]>}
 */
async function renderOrderPrices(orderID){
    // Renders data in the price services table

    const orderPricesData = await api.orders.readOrderPrices(orderID);
    if (orderPricesData !== undefined){
        const parsedData = parsers.parseOrderPrices(orderPricesData);
        return parsedData.map(el => {
            const {orderPriceID, unitPrice, serviceID, serviceName, serviceType} = el
            const item = document.getElementById('orderServicePriceListTemplate').content.cloneNode(true);
            const div = item.querySelector('div');
            div.setAttribute('data-id', orderPriceID);
            const spans = item.querySelectorAll('label span');
            spans[0].textContent = serviceID;
            spans[1].textContent = `${serviceName} ${serviceType}`;
            const input = div.querySelector('input');
            input.value = unitPrice;
            input.setAttribute('data-value', unitPrice)
            const buttons = item.querySelectorAll('a');
            buttons[0].addEventListener('click', (ev) => {
                ev.preventDefault();
                input.disabled = false;
                buttons.forEach(el => el.classList.toggle('d-none'));
            })
            buttons[1].addEventListener('click', async (ev) => {
                ev.preventDefault();
                let newValue = input.value
                const data = {
                    'id': orderPriceID,
                    'unit_price': newValue
                }
                const result = await api.orders.updateOrderPrices(data);
                if (result !== undefined){
                    buttons.forEach(el => el.classList.toggle('d-none'));
                    input.disabled = true;
                    input.dataset.value = newValue;
                }
            })
            buttons[2].addEventListener('click', (ev) => {
                ev.preventDefault();
                buttons.forEach(el => el.classList.toggle('d-none'));
                input.disabled = true;
                input.value = input.dataset.value;
            })

            return item;
        })
    } else {
        return [];
    }
}

/**
 * Gets orderServicesData and renders a list of items for the orderPricesList
 * @param orderID {string|number} ID for which to generate the service prices
 * @return {Promise<Node[]>}
 */
async function renderOrderServices(orderID){
    // Renders the data in the order services table

    const data = await api.orders.readOrderServices(orderID);
    if (data !== undefined){
        const orderServicesData = parsers.parseOrderServices(data);
        return renderOrderServicesItems(orderServicesData);
    }
}

/**
 * Renders a list of orderServices items
 * @param orderServicesData list of parsed orderServicesData
 * @return {Node[]}
 */
function renderOrderServicesItems(orderServicesData){
    return Object.entries(orderServicesData)
    .sort((a, b) => {
        return a[0] - b[0];
    })
    .map(el => {
        const [_, details] = el;
        const {description, serviceID,  accounts, orderServiceId} = details;
        const item = document.getElementById('orderServiceListTemplate').content.cloneNode(true);
        const spans = item.querySelectorAll('span');
        const accountList = accounts.join(', ');
        [serviceID, description, accountList, accountList].forEach((el, i) => {spans[i].textContent = el});
        const collapseBtn = item.querySelector('.btn');
        collapseBtn.setAttribute('data-bs-target', `#${orderServiceId}multiCollapse`);
        const collapseItem = item.querySelector('#multiCollapse');
        collapseItem.id = `${orderServiceId}multiCollapse`;
        collapseItem.addEventListener('show.bs.collapse', () => {
            spans[2].textContent = `Number of accounts: ${accounts.length}`;
        });
        collapseItem.addEventListener('hide.bs.collapse', () => {
            spans[2].textContent = spans[3].textContent;
        });
        return item;
    });
}

// Utils

/**
 * Stores contractData to sessionStorage under 'contract${contractID}'
 * @param parsedData Contract data to store
 */
function storeContractDetails(parsedData){
    const {contractID} = parsedData;
    sessionStorage.setItem(`contract${contractID}`, JSON.stringify(parsedData));
}

/**
 * Stores orderData to sessionStorage under 'order${contractID}'
 * @param parsedData Order data to store
 */
function storeOrderDetails(parsedData){
    const {orderID} = parsedData;
    sessionStorage.setItem(`order${orderID}`, JSON.stringify(parsedData));
}