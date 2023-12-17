import {modalShow, getPreviousPeriod, modalClose} from "./utils.js";
import {api} from "./api.js";

const refreshInterval = 2000;
const maxSecondsToUpdate = 300;

export async function periodModalObject(modalParams){

    // Set constants for easy access
    const {modalTitle, modalScopeFunc, clientID, accountID, programScope} = modalParams
    const modal = document.getElementById('periodModal');
    const periodSelector = modal.querySelector('#periodModalPeriod');
    const scopeSelector = modal.querySelector('#periodModalScopeSelect');
    const executionTime = modal.querySelector('#periodModalExecutionTime');
    const startButton = modal.querySelector('#periodModalStartButton');
    const progressStatusField = modal.querySelector('#progressSection p');
    const progressBar = modal.querySelector('#periodModalProgressBar');
    const periodModalList = modal.querySelector('#periodModalList');
    const progressSection = modal.querySelector('#progressSection')
    let seconds;
    let processedFiles = [];

    // Customize modal
    modal.querySelector('#periodModalHeading').textContent = modalTitle;
    periodSelector.value = getPreviousPeriod();
    progressSection.classList.add('d-none');
    startButton.classList.remove('d-none')
    resetCounter();

    // Return a trigger function for launching the modal
    return async (callBack) => {

        // Refresh the modal UI
        await refreshModal();

        // Set the Start button listener
        startButton.addEventListener('click',onStartButtonClick,{once: true});
        modal.querySelector('div.modal-header button').addEventListener('click', () => {
            startButton.removeEventListener('click', onStartButtonClick);
            modalClose(modal.id);
        }, {once: true})

        modalShow(modal.id);

        async function onStartButtonClick() {
            await buttonClick(callBack);
        }
    }

    // Support functions
    async function buttonClick(callBack){
        // This function is assigned to the event listener of the Start button

        // Hide button after click, show progress and start counter
        startButton.classList.add('d-none');
        progressSection.classList.remove('d-none');
        const counter = startCounter();

        // Get the async call task_id
        let response;
        if (programScope === 'reports' && clientID !== undefined){
            response = await generateReport();
        } else if (programScope === 'usage' && accountID !== undefined) {
            response = await calculateUsage();
        } else {
            throw Error ('Wrong modal configuration');
        }
        const {'taskId': taskID} = response

        // Start the task update loop and once finished call the callBack
        try {
            await updateTaskProgress(taskID);
        } catch (err) {
            console.error('Error in updateTaskProgress:', err);
        } finally {
            clearInterval(counter);
            if (callBack !== undefined){
                callBack();
            }
        }
    }

    async function calculateUsage(){
        const scopeParams = {
            'period': periodSelector.value,
            'vendor': scopeSelector.value
        };
        return await api.accounts.calculateUsage(scopeParams);
    }

    async function generateReport(){
        let scopeParams = {'period': periodSelector.value};
        if (scopeSelector.value === '0'){
            scopeParams['client'] = clientID;
            return await api.reports.generateClientReports(scopeParams);
        } else {
            scopeParams['report'] = scopeSelector.value;
            return await api.reports.generateReports(scopeParams);
        }
    }

    async function refreshModal(){
        let scopeData = modalScopeFunc();
        if (scopeData instanceof Promise) {
            scopeData = await scopeData;
        }
        const scopeOptions = scopeData.map(el => {
            const {id, description} = el;
            let opt = document.createElement('option');
            opt.value = id;
            opt.textContent = description;
            return opt;
        });
        scopeSelector.replaceChildren(...scopeOptions);
        progressSection.classList.add('d-none');
        progressStatusField.textContent = '';
        progressBar.classList.add('bg-success');
        progressBar.classList.remove('bg-warning');
        progressBar.style.width = `0%`;
        progressBar.textContent = `0%`;
        periodModalList.replaceChildren();
        processedFiles.length = 0;
        resetCounter();
        startButton.classList.remove('d-none');
    }

    function resetCounter(){
        seconds = 0;
        executionTime.classList.add('d-none');
    }

    function startCounter() {
        executionTime.classList.remove('d-none');
        return setInterval(() => {
            seconds += 1;
            const m = Math.floor(seconds / 60);
            const s = seconds % 60;
            executionTime.innerText = `Execution time: ${m}m ${s}s`;
        }, 1000);
    }

    async function updateTaskProgress(taskID) {
        let taskComplete = false;
        while (!taskComplete && seconds <= maxSecondsToUpdate){

            // Delay before the start of loop cycle
            if (!taskComplete){
                await new Promise(resolve => setTimeout(resolve, refreshInterval));
            }

            // Fetch task status data
            const response = await api.readTaskStatus(taskID);
            if (response === undefined) {
                throw new Error('API response is undefined');
            } else {
                const {
                    'status': taskStatus,
                    'number_of_files': fileCount,
                    'progress': taskProgress,
                    'processed_documents': fileList = [],
                    'note': note
                } = response;

                // Update task status
                let progressStatus = 'Processing...';
                if (fileCount !== 0 && fileCount !== undefined) {
                    progressStatus = `Processed files ${fileList.length}/${fileCount}`;
                }
                progressStatusField.textContent = progressStatus;
                progressBar.style.width = `${taskProgress}%`;
                progressBar.textContent = `${taskProgress}%`;

                // Update file list
                for (const file of fileList){
                    const {fileName} = file;
                    if (!processedFiles.includes(fileName)){
                        processedFiles.push(fileName);
                        let li = renderFileListItem(file);
                        periodModalList.insertBefore(li, periodModalList.firstChild);
                    }
                }

                // Check if task is complete
                taskComplete = (taskStatus !== 'PROGRESS');
                if (taskComplete){
                    progressBar.classList.remove('progress-bar-striped');
                    if (taskStatus === 'FAILED'){
                        progressStatusField.textContent = note;
                        progressBar.textContent = 'Report generation failed';
                        progressBar.classList.remove('bg-success');
                        progressBar.classList.add('bg-danger');
                    }
                }
            }
        }
    }

    function renderFileListItem(data) {

        const { fileId, fileName, resultCode, resultText } = data;
        const item = document.getElementById('periodModalListItem').content.cloneNode(true);
        const listItem = item.querySelector('a');

        listItem.textContent = `${fileName} (${resultText})`;
        listItem.setAttribute('data-id', fileId);
        if (resultCode === 0) {
            listItem.classList.add('text-success');
            // If modal used for report generation provide download link
            if (programScope === 'reports'){
                listItem.href = `/reports/download/billing/file/${fileId}/`;
            }
        } else if (resultCode === 3) {
            listItem.classList.add('text-secondary');
        } else if (resultCode === 4) {
            listItem.classList.add('text-warning');
        } else {
            listItem.classList.add('text-danger');
        }
        return item;
    }
}

