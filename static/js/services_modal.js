import {modalClose, modalShow, parsers} from "./utils.js";
import {getRecords} from "./api.js";

/**
 * Sets-up a servicesModal
 * @param paginated {boolean} 'true' if the modal should be expecting paginated data
 * @return {(function(*, *, function): void)|*}
 */
export function servicesModalObject(paginated=false){

    // Set-up modal
    const modal = document.getElementById('modalClientServices');
    const servicesList = modal.querySelector('#modalClientServiceList');
    const clientServicesItemTemplate = document.getElementById('clientServicesItemTemplate');
    modal.querySelectorAll('.modal-footer li a').forEach((btn, i)=>{
        btn.addEventListener('click', (ev)=>{
           ev.preventDefault();
           servicesList.querySelectorAll('input').forEach(el=>el.checked = i===0)
        });
    });

    // Set-up infinite scroll
    const loadThreshold = 800;
    let allowScroll, distanceToEnd, nextURL;
    if (paginated){
        servicesList.addEventListener('scroll', async ()=>{
            if (allowScroll){
                distanceToEnd = getScroll();
                if (distanceToEnd < loadThreshold){
                    allowScroll = false;
                    let data = await getRecords(nextURL);
                    if (data !== undefined){
                        const {next, results} = parsers.parseClientServicesPages(data);
                        servicesList.append(...renderElements(results));
                        nextURL = next;
                        allowScroll = next !== null;
                    }
                }
            }
        })
    }

    // Declare helper functions
    function getScroll(){
        return Math.abs(servicesList.scrollHeight - servicesList.scrollTop - servicesList.clientHeight);
    }
    function renderElements(elData){
        return elData.map(el=>{
            const {accountID, accountServiceID, serviceID, description, serviceName, serviceType, filterOverride} = el;
            const item = clientServicesItemTemplate.content.cloneNode(true);

            // Set description and pills
            const spans = item.querySelectorAll('span');
            [description, accountID, serviceID, serviceName, serviceType].forEach((el, i)=> spans[i].textContent = el)
            if (filterOverride !== undefined){
                spans[5].textContent = `${filterOverride}`
            }

            // Set data-id depending on availability of accountServiceID or serviceID
            const itemID = accountServiceID !== undefined ? accountServiceID : serviceID;
            const aTag = item.querySelector('a');
            aTag.setAttribute('data-id', itemID);
            aTag.addEventListener('click', (ev) => {
                ev.preventDefault();
                aTag.querySelector('input').checked = !aTag.querySelector('input').checked
            });
            return item;
        });
    }

    // Return
    return (modalConfig, servicesData, callBack) => {

        // Customize modal
        const {modalHeader, btnText, remove} = modalConfig;
        const addBtnClass = remove ? 'btn-danger' : 'btn-primary';
        const removeBtnClass = remove ? 'btn-primary' : 'btn-danger';
        modal.querySelector('#addServicesLabel').textContent = modalHeader;
        const modalButtons = modal.querySelectorAll('div.modal-footer button');
        modalButtons.forEach(el=> {
            el.classList.add(addBtnClass);
            el.classList.remove(removeBtnClass);
        });
        modal.querySelector('#btnUpdateServicesText').textContent = btnText;

        // Get data and activate infinite scroll
        let data = servicesData;
        if (paginated){
            const {next, results} = data;
            data = results;
            allowScroll = next !== null;
            if (next !== null){
                nextURL = next;
            }
        }

        // Render initial services list
        if (data.length > 0){
            const listData = renderElements(data)
            servicesList.replaceChildren(...listData);
        } else {
            const div = document.createElement('div');
            div.classList.add('list-group-item');
            div.appendChild(document.createTextNode('No data'));
            servicesList.replaceChildren(div);
        }

        // Add listeners
        modalButtons[0].addEventListener('click', async ()=> {
            const spinner = modal.querySelector('#btnUpdateServicesSpinner');
            spinner.classList.toggle('d-none');
            const selectedItems = Array.from(servicesList.querySelectorAll('input'))
                .filter(el=>el.checked)
                .map(el=>el.closest('a.list-group-item').dataset.id);
            void await callBack(selectedItems);
            spinner.classList.toggle('d-none');
            modalClose(modal.id);
        }, {once: true});

        // Show modal
        modalShow(modal.id);
    }
}
