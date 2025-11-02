// Main JavaScript for KvízAréna PWA

// Global state
const appState = {
    sessionId: null,
    quizName: '',
    timeLimit: 15,
    userId: null,
    // Cached data
    quizzes: [],
    stats: null,
    leaderboard: null
};

let deferredPrompt; // For PWA install prompt

// Timer state variables
let gameTimer = null; // ID for requestAnimationFrame
let timerDuration = 15; // Default duration

// Initialize the application
document.addEventListener('DOMContentLoaded', initialize);

function initialize() {
    console.log('KvízAréna initialized');
    
    // Register service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('Service Worker registered:', registration);
            })
            .catch(error => {
                console.error('Service Worker registration failed:', error);
            });
    }
    
    checkLoginStatus(); // Check if user is logged in
    
    // Handle click-to-toggle for the user dropdown
    const userInfo = document.getElementById('user-info');
    const userDropdown = document.querySelector('.user-dropdown');
    
    if (userInfo && userDropdown) {
        userInfo.addEventListener('click', (event) => {
            event.stopPropagation(); // Stop the click from bubbling up to the window
            userDropdown.classList.toggle('show');
        });
        
        // Add a global click listener to close the menu
        window.addEventListener('click', (event) => {
            // If the dropdown is open and the click was *not* inside the user info area
            if (userDropdown.classList.contains('show') && !userInfo.contains(event.target)) {
                userDropdown.classList.remove('show');
            }
        });
    }
    
    // Add navigation event handlers
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const screen = e.currentTarget.dataset.screen;

            // Update active link
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            e.currentTarget.classList.add('active');

            // Show the screen
            showScreen(screen);
        });
    });
    
    // Handle hash changes
    window.addEventListener('hashchange', handleHashChange);
    handleHashChange(); // Handle initial page load
    
    // --- ADD PWA INSTALL PROMPT LOGIC ---
    window.addEventListener('beforeinstallprompt', (e) => {
        // Prevent the mini-infobar from appearing
        e.preventDefault();
        // Stash the event so it can be triggered later.
        deferredPrompt = e;
        // Show our custom install button
        const installBtn = document.getElementById('install-app-btn');
        if (installBtn) {
            installBtn.style.display = 'block';
        }
    });

    document.getElementById('install-app-btn').addEventListener('click', async (e) => {
        e.preventDefault();
        // Hide the button
        const installBtn = document.getElementById('install-app-btn');
        if (installBtn) {
            installBtn.style.display = 'none';
        }
        // Show the install prompt
        if (deferredPrompt) {
            deferredPrompt.prompt();
            // Wait for the user to respond to the prompt
            const { outcome } = await deferredPrompt.userChoice;
            console.log(`User response to the install prompt: ${outcome}`);
            // We've used the prompt, and can't use it again.
            deferredPrompt = null;
        }
    });
    // --- END PWA LOGIC ---
}

// Hash routing
function handleHashChange() {
    const hash = window.location.hash || '#home';
    const navLink = document.querySelector(`.nav-link[href="${hash}"]`);
    if (navLink) {
        navLink.click();
    } else {
        const homeLink = document.querySelector('.nav-link[href="#home"]');
        if (homeLink) homeLink.click();
    }
}

// Start the timer loop with visual progress ring
function startTimerLoop(duration) {
    timerDuration = duration;
    let startTime = Date.now();

    // Find the new elements
    const timerProgress = document.getElementById('timer-bar-progress');
    const timerText = document.getElementById('timer-bar-text');

    // Check if timer elements exist
    if (!timerProgress || !timerText) {
        console.error('Timer elements not found in DOM');
        return;
    }

    // Reset (set to full bar)
    timerProgress.style.width = '100%';
    timerProgress.classList.remove('warning');
    timerText.classList.remove('warning');

    function timerStep() {
        const elapsedMs = Date.now() - startTime;
        const elapsedSec = elapsedMs / 1000;
        let remainingSec = duration - elapsedSec;

        if (remainingSec <= 0) {
            remainingSec = 0;

            // Time's up
            cancelAnimationFrame(gameTimer);
            timerText.textContent = 0;
            timerProgress.style.width = '0%';

            // Automatically submit a blank answer
            console.log("Time's up!");
            submitAnswer(""); // Submit blank
            return;
        }

        // Update text
        timerText.textContent = Math.ceil(remainingSec);

        // Update progress bar width
        const fraction = remainingSec / duration;
        timerProgress.style.width = (fraction * 100) + '%';

        // Warning (last 5 seconds)
        if (remainingSec <= 5) {
            timerProgress.classList.add('warning');
            timerText.classList.add('warning');
        }

        // Continue the loop
        gameTimer = requestAnimationFrame(timerStep);
    }

    // Start the loop
    gameTimer = requestAnimationFrame(timerStep);
}

// Check login status
async function checkLoginStatus() {
    try {
        const response = await fetch('/api/game/user/me');
        const user = await response.json();

        if (response.ok) {
            // User is logged in
            appState.userId = user.user_id;
            document.getElementById('user-name').textContent = user.name;
            document.getElementById('user-avatar').src = user.picture || 'default-avatar.png';
            document.getElementById('user-info').style.display = 'flex';

            fetchQuizzes(); // Fetch quizzes now
            window.location.hash = '#home';
            handleHashChange();

        } else {
            // Auth failed (e.g., user deleted from DB, or 404 error).
            // Force logout to clear the bad session cookie.
            window.location.href = '/api/auth/logout';
        }
    } catch (e) {
        console.error("Auth check failed", e);
        // Also force logout on any failure
        window.location.href = '/api/auth/logout';
    }
}

// Fetch all available quizzes
async function fetchQuizzes() {
    try {
        const response = await fetch('/api/game/quizzes');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        appState.quizzes = await response.json();
        renderHomeScreen(appState.quizzes);
    } catch (error) {
        console.error('Error fetching quizzes:', error);
        showError('screen-home', 'Nepodařilo se načíst kvízy. Zkuste to prosím znovu.');
    }
}

// Render the home screen with quiz list
function renderHomeScreen(quizzes) {
    const container = document.getElementById('screen-home');
    container.innerHTML = '';
    
    if (quizzes.length === 0) {
        container.innerHTML = '<p class="loading">Žádné kvízy nejsou k dispozici.</p>';
        return;
    }
    
    // 1. Filter quizzes
    const onDemandQuizzes = quizzes.filter(q => q.mode === 'on_demand');
    const scheduledQuizzes = quizzes.filter(q => q.mode === 'scheduled');

    // 2. Render Scheduled Quizzes
    container.innerHTML += '<h2><i class="fas fa-stopwatch"></i> Soutěžní kvízy</h2>';
    if (scheduledQuizzes.length > 0) {
        scheduledQuizzes.forEach(quiz => {
            container.appendChild(createQuizButton(quiz));
        });
    } else {
        container.innerHTML += '<p>Momentálně nejsou naplánované žádné soutěžní kvízy.</p>';
    }

    // 3. Render On-Demand Quizzes
    container.innerHTML += '<h2><i class="fas fa-play-circle"></i> Volné kvízy</h2>';
    if (onDemandQuizzes.length > 0) {
        onDemandQuizzes.forEach(quiz => {
            container.appendChild(createQuizButton(quiz));
        });
    } else {
        container.innerHTML += '<p>Žádné volné kvízy nejsou k dispozici.</p>';
    }
}

// Helper function to create quiz button
function createQuizButton(quiz) {
    const button = document.createElement('button');
    button.className = 'quiz-button';
    button.dataset.quizId = quiz.id;

    const mainText = document.createElement('div');
    mainText.textContent = quiz.nazev;
    button.appendChild(mainText);

    const info = document.createElement('div');
    info.className = 'quiz-info';
    info.textContent = `${quiz.pocet_otazek} otázek`;
    if (quiz.popis) {
        info.textContent += ` • ${quiz.popis}`;
    }
    button.appendChild(info);

    button.addEventListener('click', () => startGame(quiz.id));
    return button;
}

// Start a new game
async function startGame(quizId) {
    try {
        const response = await fetch(`/api/game/start/${quizId}`, {
            method: 'POST' // No body, auth is via cookie
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            // Check for authentication error first
            if (response.status === 401) {
                alert('Nejste přihlášen(a). Prosím, přihlaste se.');
                window.location.href = '/api/auth/login/google';
            } else if (data.status === 'completed') {
                alert(`Tento kvíz jste již dokončil(a). Vaše skóre: ${data.final_score}`);
            } else if (data.status === 'scheduled') {
                alert(`Tento kvíz ještě nezačal. Začíná za ${Math.round(data.starts_in_seconds / 60)} minut.`);
            } else {
                alert('Chyba při startu hry: ' + data.error);
            }
            return;
        }
        
        // Save session data
        appState.sessionId = data.session_id;
        appState.quizName = data.quiz_name;
        appState.timeLimit = data.time_limit;
        appState.totalQuestions = data.total_questions;
        appState.score = 0;
        
        renderQuestion(data);
        showScreen('game');
    } catch (error) {
        console.error('Error starting game:', error);
        showError('screen-home', 'Nepodařilo se spustit hru. Zkuste to prosím znovu.');
    }
}

// Render a question
function renderQuestion(data) {
    const questionData = data.question || data.next_question;
    
    if (!questionData) {
        console.error('No question data available');
        return;
    }
    
    // Update game stats
    appState.currentQuestionNumber = questionData.number;
    appState.score = data.current_score || 0;
    
    // Update header
    document.getElementById('quiz-title').textContent = appState.quizName;
    document.getElementById('question-number').textContent = `Otázka ${appState.currentQuestionNumber}/${appState.totalQuestions}`;
    document.getElementById('score-display').textContent = `Skóre: ${appState.score}`;
    document.getElementById('time-limit').textContent = `Čas: ${appState.timeLimit}s`;
    
    // Update question text
    document.getElementById('question-text').textContent = questionData.text;
    
    // Clear any previous feedback messages
    const questionContainer = document.getElementById('question-container');
    const oldFeedback = questionContainer.querySelector('.feedback-message');
    if (oldFeedback) {
        oldFeedback.remove();
    }
    
    // Stop any previous timer
    if (gameTimer) {
        cancelAnimationFrame(gameTimer);
    }

    // Make sure we have the correct time limit
    // Either from data.time_limit (at start) or save it to appState
    if (data.time_limit) {
        appState.timeLimit = data.time_limit;
    }

    // Start new timer with limit from API
    startTimerLoop(appState.timeLimit);
    
    // Render answers
    const answersContainer = document.getElementById('answers-container');
    answersContainer.innerHTML = '';
    
    questionData.answers.forEach(answer => {
        const button = document.createElement('button');
        button.className = 'answer-button';
        button.textContent = answer.text;
        button.addEventListener('click', () => submitAnswer(answer.text));
        answersContainer.appendChild(button);
    });
}

// Submit an answer
async function submitAnswer(answerText) {
    // STOP TIMER IMMEDIATELY
    if (gameTimer) {
        cancelAnimationFrame(gameTimer);
        gameTimer = null;
    }
    
    // Disable all answer buttons to prevent multiple submissions
    const buttons = document.querySelectorAll('.answer-button');
    buttons.forEach(btn => btn.disabled = true);
    
    try {
        const response = await fetch('/api/game/answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: appState.sessionId,
                answer_text: answerText
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        handleAnswerResponse(data);
    } catch (error) {
        console.error('Error submitting answer:', error);
        showError('screen-game', 'Chyba při odesílání odpovědi. Zkuste to prosím znovu.');
        buttons.forEach(btn => btn.disabled = false);
    }
}

// Handle the response after submitting an answer
function handleAnswerResponse(data) {
    // Show feedback
    showFeedback(data);
    
    // Wait a moment before proceeding
    setTimeout(() => {
        if (data.quiz_finished) {
            // Stop timer if quiz finished
            if (gameTimer) {
                cancelAnimationFrame(gameTimer);
                gameTimer = null;
            }
            renderResults(data);
            showScreen('results');
        } else {
            renderQuestion(data);
        }
    }, 2000); // Wait 2 seconds to show feedback
}

// Show feedback after answering
function showFeedback(data) {
    const answersContainer = document.getElementById('answers-container');
    const buttons = answersContainer.querySelectorAll('.answer-button');
    
    // Highlight the correct answer
    buttons.forEach(btn => {
        if (btn.textContent === data.correct_answer) {
            btn.classList.add('correct');
        }
    });
    
    // Create and show feedback message
    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'feedback-message';
    
    if (data.feedback === "Time's up!") {
        feedbackDiv.classList.add('timeout');
        feedbackDiv.textContent = `⏱️ ${data.feedback} Správná odpověď: ${data.correct_answer}`;
    } else if (data.is_correct) {
        feedbackDiv.classList.add('correct');
        feedbackDiv.textContent = `✓ ${data.feedback}`;
    } else {
        feedbackDiv.classList.add('incorrect');
        feedbackDiv.textContent = `✗ ${data.feedback} - Správná odpověď: ${data.correct_answer}`;
    }
    
    const questionContainer = document.getElementById('question-container');
    questionContainer.insertBefore(feedbackDiv, answersContainer);
}

// Render final results
function renderResults(data) {
    // Find containers
    const rankingContainer = document.getElementById('results-ranking');
    const summaryContainer = document.getElementById('results-summary-container');

    // Clear old data
    rankingContainer.innerHTML = '';
    summaryContainer.innerHTML = '';

    // 1. Render Ranking
    const rank = data.ranking_summary;
    rankingContainer.innerHTML = `
        <h3>Váš výsledek: ${data.final_score} / ${data.total_questions}</h3>
        <p>Byl(a) jste lepší než <strong>${rank.players_worse}</strong> hráčů.</p>
        <p>Stejný výsledek mělo <strong>${rank.players_same}</strong> hráčů.</p>
        <p>Horší výsledek mělo <strong>${rank.players_better}</strong> hráčů.</p>
        <h4>Vaše percentilové umístění: ${rank.percentile}%</h4>
        <hr>
    `;

    // 2. Render Detailed Summary
    data.results_summary.forEach((log, index) => {
        const resultEl = document.createElement('div');
        resultEl.className = 'result-item-card';

        let answerFeedback = '';
        if (log.is_correct) {
            answerFeedback = `<p class="correct">Odpověděl(a) jste: <strong>${log.your_answer}</strong> (Správně)</p>`;
        } else if (log.your_answer === "") {
             answerFeedback = `<p class="incorrect"><strong>Čas vypršel!</strong></p>
                               <p>Správná odpověď: <strong>${log.correct_answer}</strong></p>`;
        } else {
            answerFeedback = `<p class="incorrect">Odpověděl(a) jste: <strong>${log.your_answer}</strong> (Špatně)</p>
                              <p>Správná odpověď: <strong>${log.correct_answer}</strong></p>`;
        }

        resultEl.innerHTML = `
            <h4>${index + 1}. ${log.question_text}</h4>
            ${answerFeedback}
            ${log.source_url ? `<a href="${log.source_url}" target="_blank">Zdroj / Více informací</a>` : ''}
        `;
        summaryContainer.appendChild(resultEl);
    });

    // Re-wire the 'Play Again' button
    document.getElementById('play-again-button').onclick = () => {
        fetchQuizzes();
        window.location.hash = '#home';
        handleHashChange();
    };
}

// Show a specific screen and hide others
function showScreen(screenName) {
    const screens = ['home', 'game', 'results', 'leaderboard', 'profile', 'settings'];
    
    screens.forEach(name => {
        const screen = document.getElementById(`screen-${name}`);
        if (!screen) return;

        if (name === screenName) {
            screen.classList.remove('hidden');
        } else {
            screen.classList.add('hidden');
        }
    });

    // Auto-load data when switching to a screen
    if (screenName === 'leaderboard') {
        loadLeaderboard();
    } else if (screenName === 'profile') {
        loadProfile();
    } else if (screenName === 'home') {
        fetchQuizzes(); // Re-fetch quizzes
    }
}

// Show an error message
function showError(containerId, message) {
    const container = document.getElementById(containerId);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    container.appendChild(errorDiv);
}

// Load and render leaderboard
async function loadLeaderboard() {
    const container = document.getElementById('leaderboard-container');
    if (appState.leaderboard) {
        return renderLeaderboard(appState.leaderboard); // Use cache
    }
    container.innerHTML = '<p class="loading">Načítám žebříček...</p>';

    try {
        const response = await fetch('/api/game/leaderboard/global');
        appState.leaderboard = await response.json();
        renderLeaderboard(appState.leaderboard);
    } catch (e) {
        container.innerHTML = '<p class="error">Nepodařilo se načíst žebříček.</p>';
    }
}

function renderLeaderboard(data) {
    const container = document.getElementById('leaderboard-container');
    container.innerHTML = `
        <table class="leaderboard-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Hráč</th>
                    <th>Odehráno kvízů</th>
                    <th>Průměrné skóre</th>
                </tr>
            </thead>
            <tbody>
                ${data.map((row, index) => `
                    <tr>
                        <td>${index + 1}</td>
                        <td><img src="${row.picture || 'default-avatar.png'}" class="avatar-small"> ${row.name}</td>
                        <td>${row.quizzes_played}</td>
                        <td>${row.avg_score}%</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Load and render user profile
async function loadProfile() {
    const statsContainer = document.getElementById('profile-stats-container');
    const achContainer = document.getElementById('profile-achievements-container');
    const histContainer = document.getElementById('profile-history-container');

    statsContainer.innerHTML = '<p class="loading">Načítám statistiky...</p>';
    achContainer.innerHTML = '';
    histContainer.innerHTML = '';

    try {
        const response = await fetch('/api/game/user/my-stats');
        const data = await response.json();

        // Render Detailed Stats
        const stats = data.detailed_stats;
        statsContainer.innerHTML = `
            <p>Odehráno kvízů: <strong>${stats.total_quizzes}</strong></p>
            <p>Celková přesnost: <strong>${stats.overall_accuracy.toFixed(1)}%</strong></p>
            <h4>Nejlepší témata:</h4>
            <ul>
                ${stats.by_topic.map(topic => `
                    <li>${topic.topic}: ${topic.correct_answers} správných odpovědí</li>
                `).join('')}
            </ul>
        `;

        // Render Achievements
        if (data.achievements.length > 0) {
            data.achievements.forEach(ach => {
                achContainer.innerHTML += `
                    <div class="achievement-card">
                        <i class="fas ${ach.icon_class} fa-2x"></i>
                        <div>
                            <strong>${ach.name}</strong>
                            <p>${ach.description}</p>
                        </div>
                    </div>
                `;
            });
        } else {
            achContainer.innerHTML = '<p>Zatím žádné úspěchy.</p>';
        }

        // Render History
        if (data.history.length > 0) {
            histContainer.innerHTML = `
                <table class="history-table">
                    <thead><tr><th>Kvíz</th><th>Skóre</th><th>Percentil</th><th>Datum</th></tr></thead>
                    <tbody>
                        ${data.history.map(res => `
                            <tr>
                                <td>${res.quiz_name}</td>
                                <td>${res.score}/${res.total_questions}</td>
                                <td>${res.percentile}%</td>
                                <td>${new Date(res.finished_at).toLocaleString()}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            histContainer.innerHTML = '<p>Zatím žádná historie.</p>';
        }

    } catch (e) {
        statsContainer.innerHTML = '<p class="error">Nepodařilo se načíst profil.</p>';
    }
}


