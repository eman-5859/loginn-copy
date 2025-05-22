let move_speed = 3, grativy = 0.5;
let bird = document.querySelector('.bird');
let img = document.getElementById('bird-1');
let sound_point = new Audio('sounds effect/point.mp3');
let sound_die = new Audio('sounds effect/die.mp3');

// getting bird element properties
let bird_props = bird.getBoundingClientRect();

// This method returns DOMReact -> top, right, bottom, left, x, y, width and height
let background = document.querySelector('.background').getBoundingClientRect();

let score_val = document.querySelector('.score_val');
let message = document.querySelector('.message');
let score_title = document.querySelector('.score_title');

// New DOM elements for last played status
const lastPlayedGameSpan = document.getElementById('last-played-game');
const lastPlayedTimeSpan = document.getElementById('last-played-time');
const exitGameBtn = document.getElementById('exitGameBtn'); // Get the new Exit Game button

let game_state = 'Start';
img.style.display = 'none';
message.classList.add('messageStyle');

// --- MODIFICATION START: Username Retrieval ---
let username = null;
const storedUser = localStorage.getItem('currentUser');
if (storedUser) {
    try {
        const userData = JSON.parse(storedUser);
        username = userData.username;
        console.log("Flappy Bird: Logged-in username:", username); // For debugging
    } catch (e) {
        console.error("Error parsing currentUser from localStorage in f.js:", e);
    }
}
// --- MODIFICATION END ---

// --- MODIFICATION START: saveScoreToDB and fetchLastPlayedStatus functions ---
// Function to save score to the database
async function saveScoreToDB(gameName, finalScore) {
    if (!username) {
        console.warn("Flappy Bird: Username not found. Cannot save score.");
        return;
    }

    try {
        const payload = {
            username: username,
            game: gameName,
            score: finalScore
        };

        const response = await fetch('/api/save-score', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (data.success) {
            console.log(`Flappy Bird: Score for ${gameName} saved successfully:`, data.message);
            fetchLastPlayedStatus(); // Refresh last played status after saving
        } else {
            console.error(`Flappy Bird: Failed to save score for ${gameName}:`, data.message);
        }
    } catch (error) {
        console.error('Flappy Bird: Error saving score to DB:', error);
    }
}

// Fetch and display last played game status
async function fetchLastPlayedStatus() {
    if (!username) {
        lastPlayedGameSpan.textContent = 'N/A';
        lastPlayedTimeSpan.textContent = 'N/A';
        return;
    }

    try {
        const response = await fetch(`/api/get-scores?username=${username}`);
        const data = await response.json();

        if (data.success && data.data.last_played) {
            lastPlayedGameSpan.textContent = data.data.last_played.toUpperCase();
            const lastPlayedDate = new Date(data.data.last_played_at);
            lastPlayedTimeSpan.textContent = lastPlayedDate.toLocaleString(); // Format as local date/time
        } else {
            lastPlayedGameSpan.textContent = 'N/A';
            lastPlayedTimeSpan.textContent = 'N/A';
        }
    } catch (error) {
        console.error('Error fetching last played status:', error);
        lastPlayedGameSpan.textContent = 'N/A';
        lastPlayedTimeSpan.textContent = 'N/A';
    }
}
// --- MODIFICATION END ---

document.addEventListener('keydown', (e) => {
    
    if(e.key == 'Enter' && game_state != 'Play'){
        document.querySelectorAll('.pipe_sprite').forEach((e) => {
            e.remove();
        });
        img.style.display = 'block';
        bird.style.top = '40vh';
        game_state = 'Play';
        message.innerHTML = '';
        score_title.innerHTML = 'Score : ';
        score_val.innerHTML = '0';
        message.classList.remove('messageStyle');
        play();
    }
});

function play(){
    // --- MODIFICATION START: Call fetchLastPlayedStatus on game start ---
    fetchLastPlayedStatus();
    // --- MODIFICATION END ---

    function move(){
        if(game_state != 'Play') return;

        let pipe_sprite = document.querySelectorAll('.pipe_sprite');
        pipe_sprite.forEach((element) => {
            let pipe_sprite_props = element.getBoundingClientRect();
            bird_props = bird.getBoundingClientRect();

            if(pipe_sprite_props.right <= 0){
                element.remove();
            }else{
                if(bird_props.left < pipe_sprite_props.left + pipe_sprite_props.width && bird_props.left + bird_props.width > pipe_sprite_props.left && bird_props.top < pipe_sprite_props.top + pipe_sprite_props.height && bird_props.top + bird_props.height > pipe_sprite_props.top){
                    game_state = 'End';
                    message.innerHTML = 'Game Over'.fontcolor('red') + '<br>Press Enter To Restart';
                    message.classList.add('messageStyle');
                    img.style.display = 'none';
                    sound_die.play();
                    // --- MODIFICATION START: Save score on game over ---
                    saveScoreToDB('flappy', parseInt(score_val.innerHTML));
                    // --- MODIFICATION END ---
                    return;
                }else{
                    if(pipe_sprite_props.right < bird_props.left && pipe_sprite_props.right + move_speed >= bird_props.left && element.increase_score == '1'){
                        score_val.innerHTML =+ score_val.innerHTML + 1;
                        sound_point.play();
                    }
                    element.style.left = pipe_sprite_props.left - move_speed + 'px';
                }
            }
        });
        requestAnimationFrame(move);
    }
    requestAnimationFrame(move);

    let bird_dy = 0;
    function apply_gravity(){
        if(game_state != 'Play') return;
        bird_dy = bird_dy + grativy;
        document.addEventListener('keydown', (e) => {
            if(e.key == 'ArrowUp' || e.key == ' '){
                img.src = 'Bird-2.png';
                bird_dy = -7.6;
            }
        });

        document.addEventListener('keyup', (e) => {
            if(e.key == 'ArrowUp' || e.key == ' '){
                img.src = 'Bird.png';
            }
        });

        if(bird_props.top <= 0 || bird_props.bottom >= background.bottom){
            game_state = 'End'; // Corrected from gameState to game_state
            message.style.left = '28vw';
            message.innerHTML = 'Game Over'.fontcolor('red') + '<br>Press Enter To Restart'; // Ensure message is set
            message.classList.add('messageStyle');
            img.style.display = 'none';
            sound_die.play();

            // --- MODIFICATION START: Save score on game over (duplicate check) ---
            // This block is already present, but the previous one was missing the game over message.
            // Ensure score is saved only once.
            saveScoreToDB('flappy', parseInt(score_val.innerHTML));
            // --- MODIFICATION END ---
            
            // window.location.reload(); // Removed to allow restart via Enter key
            // message.classList.remove('messageStyle'); // This should be removed only when game restarts
            return;
        }
        bird.style.top = bird_props.top + bird_dy + 'px';
        bird_props = bird.getBoundingClientRect();
        requestAnimationFrame(apply_gravity);
    }
    requestAnimationFrame(apply_gravity);

    let pipe_seperation = 0;

    let pipe_gap = 35;

    function create_pipe(){
        if(game_state != 'Play') return;

        if(pipe_seperation > 115){
            pipe_seperation = 0;

            let pipe_posi = Math.floor(Math.random() * 43) + 8;
            let pipe_sprite_inv = document.createElement('div');
            pipe_sprite_inv.className = 'pipe_sprite';
            pipe_sprite_inv.style.top = pipe_posi - 70 + 'vh';
            pipe_sprite_inv.style.left = '100vw';

            document.body.appendChild(pipe_sprite_inv);
            let pipe_sprite = document.createElement('div');
            pipe_sprite.className = 'pipe_sprite';
            pipe_sprite.style.top = pipe_posi + pipe_gap + 'vh';
            pipe_sprite.style.left = '100vw';
            pipe_sprite.increase_score = '1';

            document.body.appendChild(pipe_sprite);
        }
        pipe_seperation++;
        requestAnimationFrame(create_pipe);
    }
    requestAnimationFrame(create_pipe);
}

// --- MODIFICATION START: Exit Game Functionality ---
function exitGame() {
    window.location.href = '../dashboard.html'; // Redirect to the dashboard
}

document.addEventListener('DOMContentLoaded', () => {
    // Initial fetch of last played status when the page loads
    fetchLastPlayedStatus();

    // Event listener for the Exit Game button
    if (exitGameBtn) {
        exitGameBtn.addEventListener('click', exitGame);
    }
});
// --- MODIFICATION END ---
