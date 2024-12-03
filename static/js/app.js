document.addEventListener("DOMContentLoaded", () => {
    renderWelcomeCard();
});

function renderWelcomeCard() {
    const appDiv = document.getElementById("app");

    // Create the welcome card container
    const welcomeCard = document.createElement("div");
    welcomeCard.id = "welcomeCard";

    // Create welcome message
    const welcomeMessage = document.createElement("p");
    welcomeMessage.innerText = "Welcome to Our App!";
    welcomeMessage.className = "welcome-message";

    // Create Sign In button
    const signInButton = document.createElement("button");
    signInButton.innerText = "Sign In";
    signInButton.className = "button sign-in-button";
    signInButton.addEventListener("click", showSignInForm);

    // Create Sign Up button
    const signUpButton = document.createElement("button");
    signUpButton.innerText = "Sign Up";
    signUpButton.className = "button signUpButton";
    signUpButton.addEventListener("click", showSignUpForm);

    // Append elements to the welcome card
    welcomeCard.appendChild(welcomeMessage);
    welcomeCard.appendChild(signInButton);
    welcomeCard.appendChild(signUpButton);

    // Append the welcome card to the app div
    appDiv.appendChild(welcomeCard);

    // Trigger animation after a slight delay
    setTimeout(() => {
        welcomeCard.classList.add("show");
    }, 100);
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

function resetToWelcomeCard() {
    const signUpForm = document.getElementById("signupform");
    const signInForm = document.getElementById("signinform");
    const welcomeCard = document.getElementById("welcomeCard");

    if (signUpForm) {
        signUpForm.style.transform = "translateY(-20px)";
        signUpForm.style.opacity = "0";
        signUpForm.classList.remove("show");
        setTimeout(() => {
            signUpForm.remove();
        }, 300);
    }

    if (signInForm) {
        signInForm.style.transform = "translateY(-20px)";
        signInForm.style.opacity = "0";
        signInForm.classList.remove("show");
        setTimeout(() => {
            signInForm.remove();
        }, 300);
    }

    if (welcomeCard) {
        setTimeout(() =>{
        welcomeCard.style.transform = "translateY(20px)";
        welcomeCard.style.opacity = "0";
        }, 300)

        setTimeout(() => {
            welcomeCard.style.transform = "translateY(0)";
            welcomeCard.style.opacity = "1";
        }, 400);
    }
}