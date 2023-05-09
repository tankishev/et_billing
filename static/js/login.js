// Add listener
const login_form = document.querySelector('.form-signin');
const errMessage = document.getElementById('errMessage');
login_form.addEventListener("submit", (ev) => handleLogin(ev));

// Handle login form submission
async function handleLogin(ev) {
    ev.preventDefault();
    const spinner_wrapper = document.querySelector('.spinner-wrapper');
    if (!errMessage.classList.contains('d-none')){
        errMessage.classList.add('d-none')
    }
    spinner_wrapper.classList.remove('visually-hidden');

    try {

        // Send form data as asynchronous request to Django
        let formData = new FormData(login_form);
        let csrfToken = getCookie('csrftoken');
        console.log(csrfToken)
        let response = await fetch(login_form.action, {
            method: "POST",
            headers: {
                'X-CSRFToken': csrfToken
            },
                mode: 'same-origin',
            body: formData
        });

        if (response.ok) {
            // Redirect to success page
            const data = await response.json();
            document.location.href="/";
        } else if (response.status == 401) {
            // Display error message
            const data = await response.json();
            const { error_message } = data
            errMessage.textContent = error_message
            errMessage.classList.remove('d-none')
        }
    } catch (error) {
        // Display error message
        alert("An error occurred while logging in. Please try again later.");
        // location.reload()
        console.log(error)
    } finally {
        spinner_wrapper.classList.add('visually-hidden');
    }
}

function getCookie(name) {
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