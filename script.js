document.addEventListener('DOMContentLoaded', function() {
    // Sound effects
    const sounds = {
        click: new Audio('https://assets.mixkit.co/active_storage/sfx/2568/2568.wav'),
        hover: new Audio('https://assets.mixkit.co/sfx/preview/mixkit-arcade-game-jump-coin-216.mp3'),
        success: new Audio('https://assets.mixkit.co/sfx/preview/mixkit-achievement-bell-600.mp3')
    };

    // Sound toggle state
    let soundEnabled = true;

    // Background elements
    const background = document.querySelector('.pixel-background');
    const gameShapes = ['ps4', 'tictactoe', 'chess', 'flappybird'];
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff'];

    // Create floating pixels
    for (let i = 0; i < 50; i++) {
        createPixel();
    }

    // Pixel creation function
    function createPixel() {
        const pixel = document.createElement('div');
        pixel.className = 'pixel';

        const type = gameShapes[Math.floor(Math.random() * gameShapes.length)];
        const size = 10 + Math.random() * 30;
        const color = colors[Math.floor(Math.random() * colors.length)];
        const left = Math.random() * 100;
        const delay = Math.random() * 15;
        const duration = 10 + Math.random() * 20;
        const animation = Math.random() > 0.5 ? 'float' : 'float-alt';

        let boxShadow = '';
        switch(type) {
            case 'ps4':
                boxShadow = `0 0 ${color}, ${size}px 0 ${color}, 0 ${size}px ${color}, ${size}px ${size}px ${color}`;
                break;
            case 'tictactoe':
                boxShadow = `${size/3}px 0 ${color}, ${size*2/3}px 0 ${color}, 0 ${size/3}px ${color}, ${size}px ${size/3}px ${color}, ${size/3}px ${size*2/3}px ${color}, ${size*2/3}px ${size*2/3}px ${color}`;
                break;
            case 'chess':
                boxShadow = `${size/2}px 0 ${color}, 0 ${size/2}px ${color}, ${size}px ${size/2}px ${color}, ${size/2}px ${size}px ${color}`;
                break;
            case 'flappybird':
                boxShadow = `${size/2}px 0 ${color}, 0 ${size/2}px ${color}, ${size}px ${size/2}px ${color}, ${size/2}px ${size}px ${color}`;
                break;
        }

        pixel.style.width = `${size}px`;
        pixel.style.height = `${size}px`;
        pixel.style.left = `${left}vw`;
        pixel.style.bottom = `-${size}px`;
        pixel.style.boxShadow = boxShadow;
        pixel.style.animationName = animation;
        pixel.style.animationDuration = `${duration}s`;
        pixel.style.animationDelay = `${delay}s`;

        background.appendChild(pixel);

        pixel.addEventListener('animationend', function() {
            pixel.style.bottom = `-${size}px`;
            pixel.style.left = `${Math.random() * 100}vw`;
        });
    }

    // Mouse interaction with pixels
    document.addEventListener('mousemove', (e) => {
        const pixels = document.querySelectorAll('.pixel');
        const mouseX = e.clientX;
        const mouseY = e.clientY;

        pixels.forEach(pixel => {
            const rect = pixel.getBoundingClientRect();
            const pixelX = rect.left + rect.width / 2;
            const pixelY = rect.top + rect.height / 2;
            const distance = Math.sqrt(Math.pow(mouseX - pixelX, 2) + Math.pow(mouseY - pixelY, 2));

            if (distance < 100) {
                const angle = Math.atan2(mouseY - pixelY, mouseX - pixelX);
                pixel.style.transform = `translate(${Math.cos(angle) * 10}px, ${Math.sin(angle) * 10}px)`;
                pixel.style.opacity = '1';
            } else {
                pixel.style.transform = '';
                pixel.style.opacity = '0.7';
            }
        });
    });

    // Sound toggle
    document.querySelector('.sound-toggle').addEventListener('click', function() {
        soundEnabled = !soundEnabled;
        this.textContent = soundEnabled ? '♪' : '🔇';
        this.style.borderColor = soundEnabled ? '#00ffff' : '#ff0000';
        
        if (soundEnabled) {
            sounds.click.currentTime = 0;
            sounds.click.play();
        }
    });

    // Button sound effects
    document.querySelectorAll('.pixel-button, .character-option').forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            if (soundEnabled) {
                sounds.hover.currentTime = 0;
                sounds.hover.play();
            }
        });
        btn.addEventListener('click', () => {
            if (soundEnabled) {
                sounds.click.currentTime = 0;
                sounds.click.play();
            }
        });
    });

    // Login form submission
    document.querySelector('.login-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const loginButton = this.querySelector('.pixel-button');
        const username = this.querySelector('input[type="text"]').value;
        const password = this.querySelector('input[type="password"]').value;
        
        loginButton.textContent = 'LOADING...';
        loginButton.disabled = true;
        
        try {
            // *** ACTUAL API CALL TO YOUR BACKEND ***
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json(); // Parse the JSON response from the server
            
            if (!response.ok) { // Check for HTTP errors (e.g., 400, 401, 500)
                throw new Error(data.message || 'Login failed');
            }

            // Store user data (adjust based on what your /login endpoint returns)
            localStorage.setItem('currentUser', JSON.stringify({
                username: data.data.username, // Access username from data.data
                last_login: new Date().toISOString(),
                // token: data.token || null // If your backend sends a token, store it
                scores: data.data.scores, // Store scores from login response
                high_score: data.data.high_score // Store high_score from login response
            }));
            
            createPixelExplosion(loginButton);
            
            setTimeout(() => {
                window.location.href = 'dashboard.html?user=' + encodeURIComponent(data.data.username);
            }, 2000);
            
        } catch (error) {
            console.error('Login error:', error);
            loginButton.textContent = 'START GAME';
            loginButton.disabled = false;
            
            // Show error message
            const errorElement = document.createElement('div');
            errorElement.className = 'pixel-error';
            errorElement.textContent = error.message;
            this.appendChild(errorElement);
            
            setTimeout(() => {
                errorElement.remove();
            }, 3000);
            
            if (soundEnabled) {
                sounds.click.currentTime = 0;
                sounds.click.play();
            }
        }
    });

    // Signup form submission
    document.querySelector('.signup-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const signupButton = this.querySelector('.pixel-button');
        const username = this.querySelector('input[type="text"]').value;
        const email = this.querySelector('input[type="email"]').value;
        const password = this.querySelectorAll('input[type="password"]')[0].value;
        const confirmPassword = this.querySelectorAll('input[type="password"]')[1].value;
        
        if (password !== confirmPassword) {
            alert('Passwords do not match!');
            return;
        }
        
        signupButton.textContent = 'CREATING...';
        signupButton.disabled = true;
        
        try {
            // *** ACTUAL API CALL TO YOUR BACKEND ***
            const response = await fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, email, password })
            });

            const data = await response.json(); // Parse the JSON response from the server
            
            if (!response.ok) { // Check for HTTP errors
                throw new Error(data.message || 'Signup failed');
            }

            createPixelExplosion(signupButton);
            
            setTimeout(() => {
                document.querySelector('.signup-form').classList.remove('active-form');
                document.querySelector('.login-form').classList.add('active-form');
                signupButton.textContent = 'CREATE ACCOUNT';
                signupButton.disabled = false;
                
                if (soundEnabled) sounds.success.play();
                
                // Auto-fill login form
                document.querySelector('.login-form input[type="text"]').value = username;
                document.querySelector('.login-form input[type="password"]').focus();
            }, 2000);
            
        } catch (error) {
            console.error('Signup error:', error);
            signupButton.textContent = 'CREATE ACCOUNT';
            signupButton.disabled = false;
            
            // Show error message
            const errorElement = document.createElement('div');
            errorElement.className = 'pixel-error';
            errorElement.textContent = error.message;
            this.appendChild(errorElement);
            
            setTimeout(() => {
                errorElement.remove();
            }, 3000);
        }
    });

    // Form toggle
    document.getElementById('show-signup').addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelector('.login-form').classList.remove('active-form');
        document.querySelector('.signup-form').classList.add('active-form');
        if (soundEnabled) sounds.click.play();
    });

    document.getElementById('show-login').addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelector('.signup-form').classList.remove('active-form');
        document.querySelector('.login-form').classList.add('active-form');
        if (soundEnabled) sounds.click.play();
    });

    // Password match indicator
    const passwordInputs = document.querySelectorAll('.signup-form input[type="password"]');
    const passwordMatchIndicator = document.createElement('div');
    passwordMatchIndicator.className = 'password-match';
    passwordInputs[1].parentNode.appendChild(passwordMatchIndicator);

    passwordInputs.forEach(input => {
        input.addEventListener('input', function() {
            if (passwordInputs[0].value && passwordInputs[1].value) {
                if (passwordInputs[0].value === passwordInputs[1].value) {
                    passwordMatchIndicator.textContent = 'PASSWORDS MATCH!';
                    passwordMatchIndicator.className = 'password-match match';
                } else {
                    passwordMatchIndicator.textContent = 'PASSWORDS DO NOT MATCH!';
                    passwordMatchIndicator.className = 'password-match no-match';
                }
            } else {
                passwordMatchIndicator.textContent = '';
            }
        });
    });

    // Create Pixel Explosion Effect
    function createPixelExplosion(button) {
        const explosion = document.createElement('div');
        explosion.className = 'pixel-explosion';

        for (let i = 0; i < 20; i++) {
            const pixel = document.createElement('div');
            pixel.className = 'explosion-pixel';
            pixel.style.width = `${Math.random() * 10 + 5}px`;
            pixel.style.height = pixel.style.width;
            pixel.style.backgroundColor = `#${Math.floor(Math.random() * 16777215).toString(16)}`;
            pixel.style.animation = `explode ${Math.random() * 2 + 1}s ease-out forwards`;
            explosion.appendChild(pixel);
        }

        button.appendChild(explosion);
        
        explosion.addEventListener('animationend', () => {
            explosion.remove();
        });
    }

});