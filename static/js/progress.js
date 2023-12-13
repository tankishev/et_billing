let lastProcessedDocuments = [];
const taskProgressStatus = document.getElementById('taskStatus')
const progressBar = document.getElementById('progressBar');
const documentList = document.getElementById('documentList');
const taskId = document.getElementById('taskId').value;

async function updateTaskProgress(taskId) {
    try {
        const response = await fetch(`/tasks/task_status/${taskId}/`);
        const data = await response.json();
        const { taskStatus, taskProgress = 0, fileList = [], progressStatus } = data;

        taskProgressStatus.textContent = progressStatus;
        progressBar.style.width = `${taskProgress}%`;

        for (const file of fileList) {
            const { fileId, fileName, resultCode, resultText } = file;
            if (!lastProcessedDocuments.includes(fileName)) {

                lastProcessedDocuments.push(fileName);

                const listItem = document.createElement('li');
                listItem.textContent = `${fileName} (${resultText})`;
                listItem.classList.add('list-group-item', 'py-1');

                if (resultCode === 0) {
                    listItem.classList.add('text-success');
                } else if (resultCode === 3) {
                    listItem.classList.add('text-secondary');
                } else if (resultCode === 4) {

                    const link = document.createElement('a')
                    link.href = '#'
                    link.classList.add('text-warning')
                    link.id = fileId
                    link.textContent = listItem.textContent
                    link.addEventListener('click', showUnreconciledModal)
                    listItem.textContent = ''
                    listItem.appendChild(link)
                } else {
                    listItem.classList.add('text-danger');
                }

                documentList.insertBefore(listItem, documentList.firstChild);
          }
        }

        if (taskStatus === 'PROGRESS') {
            setTimeout(function () {
            updateTaskProgress(taskId);
          }, 1000);
        } else if (taskStatus === 'COMPLETE') {
            progressBar.classList.remove('progress-bar-striped');
        }

    } catch (error) {
        console.error('Error fetching task progress:', error);
    }
}

async function showUnreconciledModal(ev){
    ev.preventDefault();
    const docID = ev.target.id;
    const modal = document.querySelector('.modal');
    try {

      const response = await fetch(`/stats/usage/get-unreconciled/${docID}/`);
      const data = await response.json();
      const { table_values = [], services = [] } = data;

      const tableBody = document.querySelector('tbody');
      tableBody.innerHTML = '';
      table_values.forEach(el => {
          const trow = document.createElement('tr');
          trow.innerHTML = `
              <td>${el[0]}</td>
              <td>${el[1]}</td>
              <td>${el[2]}</td>
              <td>${el[3]}</td>`;
          tableBody.appendChild(trow);
      })

      const servicesUl = modal.querySelector('ul');
      servicesUl.innerHTML = '';
      services.forEach(el => {
          const listItem = document.createElement('li');
          listItem.textContent = el;
          servicesUl.appendChild(listItem);
      })

      const myModal = new bootstrap.Modal(modal, {keyboard: false});
      myModal.show();

    } catch (error) {
        console.error('Error fetching task progress:', error);
    }
}

setTimeout(async function () {
  await updateTaskProgress(taskId);
  }, 2000);