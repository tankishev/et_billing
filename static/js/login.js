import {getCookie} from "./utils.js";

const login_form = document.querySelector('.form-signin');
const errMessage = document.getElementById('errMessage');
login_form.addEventListener("submit", (ev) => handleLogin(ev));

async function handleLogin(ev) {
    ev.preventDefault();
    const spinner_wrapper = document.querySelector('.spinner-wrapper');
    if (!errMessage.classList.contains('d-none')){
        errMessage.classList.add('d-none')
    }
    spinner_wrapper.classList.remove('visually-hidden');

    try {

        let formData = new FormData(login_form);
        let csrfToken = getCookie('csrftoken');
        let response = await fetch(login_form.action, {
            method: "POST",
            headers: {
                'X-CSRFToken': csrfToken
            },
                mode: 'same-origin',
            body: formData
        });

        if (response.ok) {
            void await response.json();
            document.location.href="/";
        } else if (response.status === 401) {
            // Display error message
            const data = await response.json();
            const { error_message } = data
            errMessage.textContent = error_message
            errMessage.classList.remove('d-none')
        }
    } catch (error) {
        alert("An error occurred while logging in. Please try again later.");
        console.log(error)
    } finally {
        spinner_wrapper.classList.add('visually-hidden');
    }
}
