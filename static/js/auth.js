
async function submitSignIn() {
    const usernameInput = document.getElementById("signinUsername");
    const passwordInput = document.getElementById("signinPassword");
    
    if (!usernameInput || !passwordInput) {
        displayReplyStatus("Form elements not found. Please try again.", "statusbad", "signinform");
        return;
    }

    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
        displayReplyStatus("Please fill in both username and password fields.", "statusbad", "signinform");
        return;
    }

    try {
        const response = await fetch("/signin", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                username,
                password,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }

        // Redirect to main app page on successful login
        window.location.href = '/';

    } catch (error) {
        console.error("Signin error:", error);
        displayReplyStatus(
            error.message || "An error occurred during sign in. Please try again.",
            "statusbad",
            "signinform"
        );
    }
}

async function submitSignUp() {
    const usernameInput = document.getElementById("signupUsername");
    const passwordInput = document.getElementById("signupPassword");
    
    if (!usernameInput || !passwordInput) {
        displayReplyStatus("Form elements not found. Please try again.", "statusbad", "signupform");
        return;
    }

    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
        displayReplyStatus("Please fill in both username and password fields.", "statusbad", "signupform");
        return;
    }

    try {
        const response = await fetch("/signup", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                username,
                password,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }

        displayReplyStatus("Registration successful! You can now sign in.", "statusok", "signupform");
        
        // After successful registration, show welcome card
        setTimeout(() => {
            document.getElementById('signupform').remove();
            renderWelcomeCard();
        }, 1500);

    } catch (error) {
        console.error("Signup error:", error);
        displayReplyStatus(
            error.message || "An error occurred during registration. Please try again.",
            "statusbad",
            "signupform"
        );
    }
}

function showSignInForm() {
    const welcomeCard = document.getElementById("welcomeCard");
    const appContainer = document.getElementById("app");

    welcomeCard.style.transform = "translateY(-30px)";
    welcomeCard.style.opacity = "0";

    setTimeout(() => {
        welcomeCard.remove();
        
        // Create sign in form
        const signInForm = document.createElement("form");
        signInForm.id = "signinform";
        signInForm.innerHTML = `
            <h2>Sign In</h2>
            <label for="signinUsername">Username:</label>
            <input type="text" id="signinUsername" required>
            <label for="signinPassword">Password:</label>
            <input type="password" id="signinPassword" required>
            <div class="form-buttons">
                <button type="submit" class="button sign-in-button">Sign In</button>
                <button type="button" class="button cancel-button">Cancel</button>
            </div>
        `;

        appContainer.appendChild(signInForm);
        
        // Add event listeners
        signInForm.querySelector('.cancel-button').addEventListener('click', () => {
            signInForm.remove();
            renderWelcomeCard();
        });
        
        signInForm.addEventListener('submit', (e) => {
            e.preventDefault();
            submitSignIn();
        });

        // Trigger show animation
        setTimeout(() => signInForm.classList.add('show'), 10);
    }, 300);
}

function showSignUpForm() {
    const welcomeCard = document.getElementById("welcomeCard");
    const appContainer = document.getElementById("app");

    welcomeCard.style.transform = "translateY(-30px)";
    welcomeCard.style.opacity = "0";

    setTimeout(() => {
        welcomeCard.remove();
        
        // Create sign up form
        const signUpForm = document.createElement("form");
        signUpForm.id = "signupform";
        signUpForm.innerHTML = `
            <h2>Sign Up</h2>
            <label for="signupUsername">Username:</label>
            <input type="text" id="signupUsername" required>
            <label for="signupPassword">Password:</label>
            <input type="password" id="signupPassword" required>
            <div class="form-buttons">
                <button type="submit" class="button signUpButton">Sign Up</button>
                <button type="button" class="button cancel-button">Cancel</button>
            </div>
        `;

        appContainer.appendChild(signUpForm);
        
        // Add event listeners
        signUpForm.querySelector('.cancel-button').addEventListener('click', () => {
            signUpForm.remove();
            renderWelcomeCard();
        });
        
        signUpForm.addEventListener('submit', (e) => {
            e.preventDefault();
            submitSignUp();
        });

        // Trigger show animation
        setTimeout(() => signUpForm.classList.add('show'), 10);
    }, 300);
}

function displayReplyStatus(message, statusClass, formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    // Remove any existing status message
    const existingStatus = document.getElementById("replystatus");
    if (existingStatus) {
        existingStatus.remove();
    }

    const statusDiv = document.createElement("div");
    statusDiv.id = "replystatus";
    statusDiv.className = statusClass;
    statusDiv.textContent = message;

    form.appendChild(statusDiv);

    // Trigger animation
    setTimeout(() => {
        statusDiv.classList.add("show");
    }, 10);
}