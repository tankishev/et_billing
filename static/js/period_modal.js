import {modalShow, getPreviousPeriod} from "./utils.js";
import {api} from "./api.js";

const refreshInterval = 2000;
const maxSecondsToUpdate = 300;

export async function periodModalObject(modalParams){

    // Set constants for easy access
    const {modalTitle, modalScopeFunc, clientID} = modalParams
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
        startButton.addEventListener('click',async () => {
            startButton.classList.add('d-none');
            progressSection.classList.remove('d-none');
            const counter = startCounter();

            let response;
            let reportParams = {'period': periodSelector.value};
            if (scopeSelector.value === '0'){
                reportParams['client'] = clientID;
                response = await api.reports.generateClientReports(reportParams);
            } else {
                reportParams['report'] = scopeSelector.value;
                response = await api.reports.generateReports(reportParams);
            }
            const {'taskId': taskID} = response;

            try {
                console.log('in try block')
                await updateTaskProgress(taskID)
            } catch (err) {
                console.error('Error in updateTaskProgress:', err);
            } finally {
                clearInterval(counter);
                callBack('Finished execution can do some stuff now');
            }
        },{once: true});
        modalShow(modal.id);
    }

    // Support functions
    async function refreshModal(){
        const scopeData = await modalScopeFunc();
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
        progressBar.style.width = `0%`;
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
            console.log(response)
            if (response === undefined) {
                throw new Error('API response is undefined');
            } else {
                const {
                    'status': taskStatus,
                    'number_of_files': fileCount,
                    'progress': taskProgress,
                    'processed_documents': fileList = [],
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
                }
            }
        }
    }

    function renderFileListItem(data) {

        const { fileId, fileName, resultCode, resultText } = data;
        const item = document.getElementById('periodModalListItem').content.cloneNode(true);
        const listItem = item.querySelector('li');

        listItem.textContent = `${fileName} (${resultText})`;
        listItem.setAttribute('data-id', fileId);
        if (resultCode === 0) {
            listItem.classList.add('text-success');
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

