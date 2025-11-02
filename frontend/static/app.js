// Main JavaScript for KvízAréna PWA

// Game state object
const gameState = {
    sessionId: null,
    score: 0,
    currentQuestionNumber: 0,
    totalQuestions: 0,
    quizName: '',
    timeLimit: 0,
    userId: null
};

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
            gameState.userId = user.user_id;
            document.getElementById('user-name').textContent = user.name;
            document.getElementById('login-link').style.display = 'none';
            document.getElementById('user-info').style.display = 'inline';

            fetchQuizzes(); // Fetch quizzes now
            showScreen('quiz-list');

        } else {
            // User is not logged in
            document.getElementById('login-link').style.display = 'inline';
            document.getElementById('user-info').style.display = 'none';
            showScreen('quiz-list'); // Show the list, but they can't play
        }
    } catch (e) {
        console.error("Auth check failed", e);
        document.getElementById('login-link').style.display = 'inline';
    }
}

// Fetch all available quizzes
async function fetchQuizzes() {
    try {
        const response = await fetch('/api/game/quizzes');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        renderQuizList(data);
    } catch (error) {
        console.error('Error fetching quizzes:', error);
        showError('screen-quiz-list', 'Nepodařilo se načíst kvízy. Zkuste to prosím znovu.');
    }
}

// Render the list of quizzes
function renderQuizList(quizzes) {
    const container = document.getElementById('screen-quiz-list');
    container.innerHTML = '';
    
    if (quizzes.length === 0) {
        container.innerHTML = '<p class="loading">Žádné kvízy nejsou k dispozici.</p>';
        showScreen('quiz-list');
        return;
    }
    
    const title = document.createElement('h2');
    title.textContent = 'Vyberte kvíz';
    container.appendChild(title);
    
    quizzes.forEach(quiz => {
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
        container.appendChild(button);
    });
    
    showScreen('quiz-list');
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
        gameState.sessionId = data.session_id;
        gameState.quizName = data.quiz_name;
        gameState.timeLimit = data.time_limit;
        gameState.totalQuestions = data.total_questions;
        gameState.score = 0;
        
        renderQuestion(data);
        showScreen('game');
    } catch (error) {
        console.error('Error starting game:', error);
        showError('screen-quiz-list', 'Nepodařilo se spustit hru. Zkuste to prosím znovu.');
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
    gameState.currentQuestionNumber = questionData.number;
    gameState.score = data.current_score || 0;
    
    // Update header
    document.getElementById('quiz-title').textContent = gameState.quizName;
    document.getElementById('question-number').textContent = `Otázka ${gameState.currentQuestionNumber}/${gameState.totalQuestions}`;
    document.getElementById('score-display').textContent = `Skóre: ${gameState.score}`;
    document.getElementById('time-limit').textContent = `Čas: ${gameState.timeLimit}s`;
    
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
    // Either from data.time_limit (at start) or save it to gameState
    if (data.time_limit) {
        gameState.timeLimit = data.time_limit;
    }

    // Start new timer with limit from API
    startTimerLoop(gameState.timeLimit);
    
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
                session_id: gameState.sessionId,
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
        showScreen('quiz-list');
    };
}

// Show a specific screen and hide others
function showScreen(screenName) {
    const screens = ['login', 'quiz-list', 'game', 'results'];
    
    screens.forEach(name => {
        const screen = document.getElementById(`screen-${name}`);
        if (name === screenName) {
            screen.classList.remove('hidden');
        } else {
            screen.classList.add('hidden');
        }
    });
}

// Show an error message
function showError(containerId, message) {
    const container = document.getElementById(containerId);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    container.appendChild(errorDiv);
}
