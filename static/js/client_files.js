import {api} from "./api.js";
import {parsers} from "./utils.js"

document.querySelectorAll('#clientDetailsNav a')[3].classList.add('active');
const unvalidatedReportsList = document.getElementById('unvalidatedReportsList');
const clientID = document.getElementById('reportsList').dataset.clientId;

void await loadFiles(clientID);

async function loadFiles(clientID){
    const reportFilesData = await api.clients.readClientReports(clientID);
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