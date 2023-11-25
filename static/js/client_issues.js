import {api} from "./api.js";

document.querySelectorAll('#clientDetailsNav a')[4].classList.add('active');
const issuesList = document.getElementById('issuesList');
const clientID = issuesList.dataset.clientId;
void loadIssues();

async function loadIssues(){
    const issuesData = await api.clients.readClientIssues(clientID)
    if (issuesData !== undefined && issuesData.length > 0){
        const accordionItems = issuesData.map((el, i) => {
            const {description, values} = el;

            const item = document.getElementById('issueTopicTemplate').content.cloneNode(true)
            const heading = item.querySelector('#heading');
            heading.querySelector('span').textContent = description;
            heading.id = `heading${i}`;
            heading.querySelector('button').setAttribute('data-bs-target', `#collapse${i}`);
            item.querySelector('#collapse').id = `collapse${i}`;

            const ul = item.querySelector('ul');
            ul.replaceChildren(...values.map(data => {
                let li = document.createElement('li');
                li.classList.add('list-group-item');
                li.textContent = data;
                return li;
            }))

            return item;
        })
        issuesList.replaceChildren(...accordionItems);
    }
}