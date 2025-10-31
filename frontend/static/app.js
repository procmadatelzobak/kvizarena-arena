// Main JavaScript for KvízAréna PWA

// Game state object
const gameState = {
    sessionId: null,
    score: 0,
    currentQuestionNumber: 0,
    totalQuestions: 0,
    quizName: '',
    timeLimit: 0
};

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
    
    // Load the quiz list
    fetchQuizzes();
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
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
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
    
    // Find and highlight the buttons
    buttons.forEach(btn => {
        if (btn.textContent === data.correct_answer) {
            btn.classList.add('correct');
        } else if (btn.textContent !== data.correct_answer && !data.is_correct) {
            // If answer was wrong, we might want to highlight what they picked
            // But we need to track which button was clicked
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
    const container = document.getElementById('results-container');
    container.innerHTML = '';
    
    const scoreDiv = document.createElement('div');
    scoreDiv.className = 'final-score';
    scoreDiv.textContent = `${data.final_score} / ${data.total_questions}`;
    container.appendChild(scoreDiv);
    
    const label = document.createElement('div');
    label.className = 'score-label';
    const percentage = Math.round((data.final_score / data.total_questions) * 100);
    label.textContent = `Úspěšnost: ${percentage}%`;
    container.appendChild(label);
    
    // Add encouraging message
    const message = document.createElement('p');
    message.style.marginBottom = '30px';
    message.style.fontSize = '1.1rem';
    if (percentage >= 80) {
        message.textContent = '🎉 Výborně! Máte skvělé znalosti!';
    } else if (percentage >= 60) {
        message.textContent = '👍 Dobrá práce! Můžete to ještě zlepšit.';
    } else {
        message.textContent = '💪 Zkuste to znovu, příště to určitě půjde lépe!';
    }
    container.appendChild(message);
    
    const playAgainButton = document.createElement('button');
    playAgainButton.className = 'play-again-button';
    playAgainButton.textContent = 'Hrát znovu';
    playAgainButton.addEventListener('click', () => {
        fetchQuizzes();
    });
    container.appendChild(playAgainButton);
}

// Show a specific screen and hide others
function showScreen(screenName) {
    const screens = ['quiz-list', 'game', 'results'];
    
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
