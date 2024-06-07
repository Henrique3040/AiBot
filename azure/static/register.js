document.addEventListener('DOMContentLoaded', function () {
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username: username, password: password })
            })
            .then(response => {
                console.log('Response Status:', response.status);
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.message || 'Registration failed');
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('Server Response:', data);
                if (data.message === 'Registration successful') {
                    console.log('Redirecting to /index');
                    window.location.href = '/index';
                } else {
                    console.error('Registration failed:', data.message);
                    alert(data.message || 'Username already exists');
                }
            })
            .catch(error => {
                console.error('Registration error:', error);
                alert('Registration failed. Please try again.');
            });
        });
    } else {
        console.error('Registration form not found');
    }
});
