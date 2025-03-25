// Debug socket connection
const socket = io({
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
});

// Socket connection events for debugging
socket.on('connect', function() {
    console.log('Socket connected successfully, ID:', socket.id);
});

socket.on('disconnect', function(reason) {
    console.log('Socket disconnected:', reason);
});

socket.on('connect_error', function(error) {
    console.error('Connection error:', error);
});

// Enhanced sendChatMessage function
function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const message = chatInput.value.trim();
    
    if (message && userId && teamId) {
        console.log('Sending chat message:', message);
        console.log('User ID:', userId);
        console.log('Team ID:', teamId);
        
        // Check if message contains trigger words
        const triggerWords = ["thought", "thoughts", "advice", "input", "feedback", "?"];
        const containsTrigger = triggerWords.some(trigger => message.toLowerCase().includes(trigger));
        
        if (containsTrigger) {
            console.log('Message contains trigger word for AI response');
        }
        
        socket.emit('team_chat', {
            user_id: userId,
            team_id: teamId,
            message: message
        }, function(acknowledgement) {
            // This is a callback that will be called when the server receives the message
            console.log('Message acknowledgement:', acknowledgement);
        });
        
        chatInput.value = '';
    } else {
        if (!message) console.log('No message to send');
        if (!userId) console.log('No user ID');
        if (!teamId) console.log('No team ID');
    }
}

// Full event listener for document loading
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const loginSection = document.getElementById('login-section');
    const gameSection = document.getElementById('game-section');
    const teamActionSelect = document.getElementById('team-action');
    const createTeamSection = document.getElementById('create-team-section');
    const joinTeamSection = document.getElementById('join-team-section');
    const decisionPanel = document.getElementById('decision-panel');
    
    // Socket.io connection setup with error handling
    const socket = io({
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
    });
    
    let userId = null;
    let teamId = null;
    
    // Socket connection monitoring
    socket.on('connect', function() {
        console.log('Socket connected successfully, ID:', socket.id);
    });
    
    socket.on('disconnect', function(reason) {
        console.log('Socket disconnected:', reason);
    });
    
    socket.on('connect_error', function(error) {
        console.error('Connection error:', error);
    });
    
    // Socket event listeners for game functionality
    
    // Handle incoming messages
    socket.on('team_message', function(data) {
        console.log('Team message received:', data);
        handleTeamMessage(data);
    });
    
    // Handle scenario updates
    socket.on('scenario_update', function(data) {
        console.log('Scenario update received:', data);
        handleScenarioUpdate(data);
    });
    
    // Handle scenario history
    socket.on('scenario_history', function(data) {
        console.log('Scenario history received:', data);
        handleScenarioHistory(data);
    });
    
    // Handle typing indicators
    socket.on('typing_indicator', function(data) {
        console.log('Received typing indicator:', data);
        
        const messagesDiv = document.getElementById('chat-messages');
        const userId = data.user_id;
        
        // Remove any existing typing indicator for this user
        const existingIndicator = document.getElementById(`typing-${userId}`);
        if (existingIndicator) {
            messagesDiv.removeChild(existingIndicator);
        }
        
        // If user is typing, add a new indicator
        if (data.is_typing) {
            console.log(`Adding typing indicator for ${data.user_name}`);
            
            const indicatorEl = document.createElement('div');
            indicatorEl.id = `typing-${userId}`;
            indicatorEl.className = 'typing-indicator';
            indicatorEl.textContent = `${data.user_name} (${data.role}) is typing...`;
            
            messagesDiv.appendChild(indicatorEl);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    });
    
    // Show loading state while waiting for scenario update
    socket.on('submission_received', function() {
        console.log('Submission received by server');
        document.getElementById('scenario-display').innerHTML = 
            '<div class="loading">Analyzing situation and generating response...</div>';
    });
    
    // Handle errors
    socket.on('error', function(data) {
        console.error('Error from server:', data);
        alert(data.message);
    });
    
    // UI Event Listeners
    
    // Toggle between create/join team sections
    teamActionSelect.addEventListener('change', function() {
        if (this.value === 'create') {
            createTeamSection.style.display = 'block';
            joinTeamSection.style.display = 'none';
        } else {
            createTeamSection.style.display = 'none';
            joinTeamSection.style.display = 'block';
            // Load teams immediately when switching to join team option
            loadAvailableTeams();
        }
    });
    
    // Also load teams when the page initially loads if join team is selected
    if (teamActionSelect.value === 'join') {
        loadAvailableTeams();
    }
    
    // Refresh teams button
    document.getElementById('refresh-teams').addEventListener('click', loadAvailableTeams);
    
    // Join game button
    document.getElementById('join-button').addEventListener('click', handleJoinGame);
    
    // Send chat message
    document.getElementById('send-button').addEventListener('click', function() {
        sendChatMessage();
    });
    
    // Send chat on Enter key
    document.getElementById('chat-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    });
    
    // Submit decision
    document.getElementById('submit-decision').addEventListener('click', function() {
        submitTeamDecision(this);
    });
    
    // Debug test button for AI responses
    const testButton = document.getElementById('test-ai-response');
    if (testButton) {
        testButton.addEventListener('click', function() {
            console.log('Test button clicked');
            if (userId && teamId) {
                socket.emit('team_chat', {
                    user_id: userId,
                    team_id: teamId,
                    message: "Thoughts on our current situation?"
                });
                console.log("Test message sent");
            } else {
                console.log("Not in a team yet");
                alert("You must join a team first before testing AI responses");
            }
        });
    }
    
    // Expose a test function to the window object for debugging
    window.testAIResponse = function() {
        if (teamId) {
            socket.emit('team_chat', {
                user_id: userId,
                team_id: teamId,
                message: "Thoughts on our current situation?"
            });
            console.log("Test message sent through window function");
        } else {
            console.log("Not in a team yet");
        }
    };
    
    // Function to send chat messages with debugging
    function sendChatMessage() {
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();
        
        if (message && userId && teamId) {
            console.log('Sending chat message:', message);
            console.log('User ID:', userId);
            console.log('Team ID:', teamId);
            
            // Check if message contains trigger words
            const triggerWords = ["thought", "thoughts", "advice", "input", "feedback", "?"];
            const containsTrigger = triggerWords.some(trigger => message.toLowerCase().includes(trigger));
            
            if (containsTrigger) {
                console.log('Message contains trigger word for AI response');
            }
            
            socket.emit('team_chat', {
                user_id: userId,
                team_id: teamId,
                message: message
            });
            
            chatInput.value = '';
        } else {
            if (!message) console.log('No message to send');
            if (!userId) console.log('No user ID');
            if (!teamId) console.log('No team ID');
        }
    }
    
    /**
     * Load available teams for joining
     */
    async function loadAvailableTeams() {
        try {
            const response = await fetch('/api/teams');
            const data = await response.json();
            
            // Get the dropdown element
            const teamsDropdown = document.getElementById('existing-teams');
            
            // Clear existing options (except the first one)
            while (teamsDropdown.options.length > 1) {
                teamsDropdown.remove(1);
            }
            
            // Add teams to the dropdown
            data.teams.forEach(team => {
                const option = document.createElement('option');
                option.value = team.id;
                option.textContent = `${team.name} (${team.member_count} members)`;
                teamsDropdown.appendChild(option);
            });
            
            // If no teams are available, show a message
            if (data.teams.length === 0) {
                const option = document.createElement('option');
                option.value = "";
                option.textContent = "No teams available - create a new one";
                option.disabled = true;
                teamsDropdown.appendChild(option);
            }
        } catch (error) {
            console.error('Error loading teams:', error);
        }
    }
    
    /**
     * Handle joining or creating a game
     */
    async function handleJoinGame() {
        const username = document.getElementById('username').value.trim();
        const role = document.getElementById('role').value;
        
        if (!username) {
            alert('Please enter your name');
            return;
        }
        
        try {
            if (teamActionSelect.value === 'create') {
                await createNewTeam(username, role);
            } else {
                await joinExistingTeam(username, role);
            }
            
            // Join the team's socket room
            socket.emit('join_team', {
                user_id: userId,
                team_id: teamId,
                get_history: true
            });
            
            // Switch to game view
            loginSection.style.display = 'none';
            gameSection.style.display = 'block';
            
            // Show/hide decision panel based on role
            if (role === 'Team Leader') {
                decisionPanel.style.display = 'block';
            } else {
                decisionPanel.style.display = 'none';
            }
            
        } catch (error) {
            console.error('Error joining game:', error);
            alert('An error occurred. Please try again.');
        }
    }
    
    /**
     * Create a new team and game
     */
    async function createNewTeam(username, role) {
        const teamName = document.getElementById('team-name').value.trim();
        const scenarioText = document.getElementById('scenario-input').value.trim();
        
        if (!teamName || !scenarioText) {
            throw new Error('Please enter a team name and scenario');
        }
        
        // Create a new game
        const gameResponse = await fetch('/api/games', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({scenario: scenarioText})
        });
        const gameData = await gameResponse.json();
        
        // Create a team
        const teamResponse = await fetch('/api/teams', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: teamName,
                game_id: gameData.game_id
            })
        });
        const teamData = await teamResponse.json();
        teamId = teamData.team_id;
        
        // Create user
        await createUser(username, role);
    }
    
    /**
     * Join an existing team
     */
    async function joinExistingTeam(username, role) {
        teamId = document.getElementById('existing-teams').value;
        if (!teamId) {
            throw new Error('Please select a team');
        }
        
        // Create user
        await createUser(username, role);
    }
    
    /**
     * Create a user in the selected team
     */
    async function createUser(username, role) {
        const userResponse = await fetch('/api/users', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: username,
                role: role,
                team_id: teamId
            })
        });
        const userData = await userResponse.json();
        userId = userData.user_id;
    }
    
    /**
     * Handle incoming team messages
     */
    function handleTeamMessage(data) {
        const messagesDiv = document.getElementById('chat-messages');
        const messageEl = document.createElement('div');
        messageEl.className = `message ${data.type}`;
        
        if (data.type === 'chat') {
            const headerEl = document.createElement('div');
            headerEl.className = 'header';
            headerEl.textContent = `${data.user_name} (${data.role})`;
            
            const contentEl = document.createElement('div');
            contentEl.textContent = data.content;
            
            messageEl.appendChild(headerEl);
            messageEl.appendChild(contentEl);
        } else {
            // System message
            messageEl.textContent = data.content;
        }
        
        messagesDiv.appendChild(messageEl);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    /**
     * Handle scenario updates
     */
    function handleScenarioUpdate(data) {
        // Update the scenario title to "Updated Situation" after first update
        document.getElementById('scenario-title').textContent = 'Updated Situation';
        
        // Update current scenario display
        document.getElementById('scenario-display').textContent = data.scenario;
        
        // Add to history
        addToScenarioHistory(data.scenario);
        
        // Reset the submit button if it exists
        const submitBtn = document.getElementById('submit-decision');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Decision';
        }
    }
    
    /**
     * Handle scenario history data
     */
    function handleScenarioHistory(data) {
        const history = data.history;
        const historyContainer = document.getElementById('history-container');
        
        // Clear existing history items
        historyContainer.innerHTML = '';
        
        // Add each scenario to history in reverse order (newest first)
        for (let i = history.length - 1; i >= 0; i--) {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            
            // Create timestamp
            const timestamp = document.createElement('span');
            timestamp.className = 'timestamp';
            const date = new Date(history[i].timestamp);
            timestamp.textContent = date.toLocaleString();
            
            // Create scenario text
            const scenarioTextEl = document.createElement('div');
            scenarioTextEl.className = 'scenario-text';
            scenarioTextEl.textContent = history[i].scenario;
            
            // Append elements to history item
            historyItem.appendChild(timestamp);
            historyItem.appendChild(scenarioTextEl);
            
            // Add to container
            historyContainer.appendChild(historyItem);
        }
    }
    
    /**
     * Add scenario to history
     */
    function addToScenarioHistory(scenarioText) {
        const historyContainer = document.getElementById('history-container');
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        
        // Create timestamp
        const timestamp = document.createElement('span');
        timestamp.className = 'timestamp';
        const now = new Date();
        timestamp.textContent = now.toLocaleString();
        
        // Create scenario text
        const scenarioTextEl = document.createElement('div');
        scenarioTextEl.className = 'scenario-text';
        scenarioTextEl.textContent = scenarioText;
        
        // Append elements to history item
        historyItem.appendChild(timestamp);
        historyItem.appendChild(scenarioTextEl);
        
        // Add to container (at the beginning to show newest first)
        historyContainer.insertBefore(historyItem, historyContainer.firstChild);
    }
    
    /**
     * Send chat message
     */
    function sendChatMessage() {
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();
        
        if (message && userId && teamId) {
            socket.emit('team_chat', {
                user_id: userId,
                team_id: teamId,
                message: message
            });
            chatInput.value = '';
        }
    }
    
    /**
     * Submit team decision
     */
    function submitTeamDecision(buttonElement) {
        const decisionInput = document.getElementById('decision-input');
        const decision = decisionInput.value.trim();
        
        if (decision && userId && teamId) {
            // Disable the button and show loading state
            if (buttonElement) {
                buttonElement.disabled = true;
                buttonElement.textContent = 'Processing...';
            } else {
                const submitBtn = document.getElementById('submit-decision');
                submitBtn.disabled = true;
                submitBtn.textContent = 'Processing...';
            }
            
            socket.emit('submit_decision', {
                user_id: userId,
                team_id: teamId,
                decision: decision
            });
            
            decisionInput.value = '';
        }
    }
    
    /**
     * Get selected AI roles from checkboxes
     */
    function getSelectedAIRoles() {
        const checkboxes = document.querySelectorAll('input[name="ai_roles"]:checked');
        const roles = Array.from(checkboxes).map(checkbox => checkbox.value);
        return roles;
    }

    // Update the createNewTeam function to include AI teammates
    async function createNewTeam(username, role) {
        const teamName = document.getElementById('team-name').value.trim();
        const scenarioText = document.getElementById('scenario-input').value.trim();
        
        if (!teamName || !scenarioText) {
            throw new Error('Please enter a team name and scenario');
        }
        
        // Get selected AI roles
        const aiRoles = getSelectedAIRoles();
        
        // Create a new game
        const gameResponse = await fetch('/api/games', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({scenario: scenarioText})
        });
        const gameData = await gameResponse.json();
        
        // Create a team with AI teammates
        const teamResponse = await fetch('/api/teams', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: teamName,
                game_id: gameData.game_id,
                ai_roles: aiRoles
            })
        });
        const teamData = await teamResponse.json();
        teamId = teamData.team_id;
        
        // Create user
        await createUser(username, role);
    }

    // Add a function to get role class for styling
    function getRoleClass(role) {
        if (role.includes('Leader')) return 'team-leader';
        if (role.includes('Military')) return 'military';
        if (role.includes('Economic')) return 'economic';
        if (role.includes('Intelligence')) return 'intelligence';
        if (role.includes('Diplomatic')) return 'diplomatic';
        return '';
    }

    // Update the handleTeamMessage function to include AI styling
    function handleTeamMessage(data) {
        const messagesDiv = document.getElementById('chat-messages');
        const messageEl = document.createElement('div');
        
        // Check if this is an AI message
        const isAI = users && users[data.user_id] && users[data.user_id].is_ai;
        
        if (data.type === 'chat') {
            messageEl.className = `message chat${isAI ? ' ai-message' : ''}`;
            
            const headerEl = document.createElement('div');
            headerEl.className = 'header';
            
            // Add name
            headerEl.textContent = data.user_name;
            
            // Add role badge
            const roleClass = getRoleClass(data.role);
            const roleBadge = document.createElement('span');
            roleBadge.className = `role-badge ${roleClass}`;
            roleBadge.textContent = data.role;
            headerEl.appendChild(roleBadge);
            
            const contentEl = document.createElement('div');
            contentEl.textContent = data.content;
            
            messageEl.appendChild(headerEl);
            messageEl.appendChild(contentEl);
        } else {
            // System message
            messageEl.className = 'message system';
            messageEl.textContent = data.content;
        }
        
        messagesDiv.appendChild(messageEl);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    // Add the typing indicator handler
    socket.on('typing_indicator', function(data) {
        const messagesDiv = document.getElementById('chat-messages');
        const userId = data.user_id;
        
        // Remove any existing typing indicator for this user
        const existingIndicator = document.getElementById(`typing-${userId}`);
        if (existingIndicator) {
            messagesDiv.removeChild(existingIndicator);
        }
        
        // If user is typing, add a new indicator
        if (data.is_typing) {
            const indicatorEl = document.createElement('div');
            indicatorEl.id = `typing-${userId}`;
            indicatorEl.className = 'typing-indicator';
            indicatorEl.textContent = `${data.user_name} (${data.role}) is typing...`;
            
            messagesDiv.appendChild(indicatorEl);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    });

    // Store user data received from server
    let users = {};

    // Update the handle_join_team socket event to store users
    socket.on('join_team', function(data) {
        // Store user data
        if (data.users) {
            users = data.users;
        }
    });
});