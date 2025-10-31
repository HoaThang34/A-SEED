(function () {
  // Small helper for query selection
  const $ = s => document.querySelector(s);

  // Form and control nodes
  const loginForm = $('#loginForm');
  const registerForm = $('#registerForm');
  const showLoginBtn = $('#showLogin');
  const showRegisterBtn = $('#showRegister');
  const authMessage = $('#authMessage');
  const adminShortcut = $('#adminShortcut');

  // Toggle: show Login, hide Register
  showLoginBtn.onclick = () => {
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
    showLoginBtn.classList.add('active');
    showRegisterBtn.classList.remove('active');
    authMessage.textContent = '';
  };

  // Toggle: show Register, hide Login
  showRegisterBtn.onclick = () => {
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
    showLoginBtn.classList.remove('active');
    showRegisterBtn.classList.add('active');
    authMessage.textContent = '';
  };

  // --- Login flow ---
  // POST /api/login with {username, password}. On success, go to /chat.
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authMessage.textContent = 'Checking...';
    const username = $('#loginUser').value;
    const password = $('#loginPass').value;

    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (res.ok) {
        window.location.href = '/chat';
      } else {
        authMessage.textContent = 'Invalid username or password.';
      }
    } catch (error) {
      authMessage.textContent = 'Could not connect to the server.';
    }
  });

  // --- Registration flow ---
  // Validate required fields and password confirmation; then POST /api/register.
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authMessage.textContent = 'Creating account...';
    const displayName = $('#regDisplayName').value;
    const username = $('#regUser').value;
    const password = $('#regPass').value;
    const confirmPassword = $('#regPassConfirm').value;

    if (!displayName || !username || !password) {
      authMessage.textContent = 'Please fill out all fields.';
      return;
    }

    if (password !== confirmPassword) {
      authMessage.textContent = 'Passwords do not match.';
      return;
    }

    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, displayName, password }),
      });

      const data = await res.json();
      if (res.ok) {
        authMessage.textContent = 'Account created successfully! Please log in.';
        showLoginBtn.click();
      } else {
        authMessage.textContent = data.error || 'Registration failed.';
      }
    } catch (error) {
      authMessage.textContent = 'Could not connect to the server.';
    }
  });

  // --- Hidden Admin Shortcut ---
  // Five quick taps within 1.5s navigates to /admin.
  let adminClickCount = 0;
  let adminClickTimer = null;
  adminShortcut.addEventListener('click', () => {
    adminClickCount++;

    clearTimeout(adminClickTimer);
    adminClickTimer = setTimeout(() => {
      adminClickCount = 0;
    }, 1500);

    if (adminClickCount >= 5) {
      window.location.href = '/admin';
    }
  });
})();
