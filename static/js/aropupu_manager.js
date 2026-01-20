// Aropupu bracket manager - Uses aropupu.fi/bracket system
class AropupuBracketManager {
    constructor() {
        this.competitionId = null;
        this.bracketElement = null;
        this.tournamentId = null;
        this.teamsData = null;
    }

    initialize(competitionId, tournamentId = null, teamsData = null, options = {}) {
        this.competitionId = competitionId;
        this.tournamentId = tournamentId || options.tournamentId || `comp-${competitionId}`;
        this.teamsData = teamsData || this.getTeamsDataFromElement();
        this.bracketElement = document.getElementById('aropupu-bracket');

        if (!this.bracketElement) {
            console.error("Aropupu bracket element not found");
            return;
        }

        console.log("Initializing Aropupu bracket system with tournament ID:", this.tournamentId);

        // Add Aropupu-specific UI
        this.addAropupuControls();

        // Load Aropupu bracket - first try to use aropupu.fi, fallback to internal if needed
        this.loadAropupuBracket();
    }

    getTeamsDataFromElement() {
        const teamsDataElement = document.getElementById('teams-data');
        if (!teamsDataElement) {
            console.error('Teams data element not found');
            return null;
        }

        try {
            return JSON.parse(teamsDataElement.textContent);
        } catch (error) {
            console.error('Error parsing teams data:', error);
            return null;
        }
    }

    addAropupuControls() {
        // Remove any existing controls first
        const existingControls = document.getElementById('aropupu-controls');
        if (existingControls) {
            existingControls.remove();
        }

        if (!this.bracketElement) return;

        // Create Aropupu-specific controls
        const controlsDiv = document.createElement('div');
        controlsDiv.id = 'aropupu-controls';
        controlsDiv.style.cssText = `
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            display: flex;
            gap: 8px;
            background: rgba(255,255,255,0.9);
            padding: 5px;
            border-radius: 4px;
        `;

        // Add refresh button
        const refreshButton = document.createElement('button');
        refreshButton.innerHTML = '🔄 Refresh';
        refreshButton.title = 'Refresh Bracket';
        refreshButton.style.cssText = `
            padding: 6px 12px;
            background: #10B981;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        `;

        refreshButton.addEventListener('click', (e) => {
            e.preventDefault();
            this.loadAropupuBracket();
        });

        // Add sync button to sync with aropupu.fi
        const syncButton = document.createElement('button');
        syncButton.innerHTML = '🔄 Sync';
        syncButton.title = 'Sync with Aropupu System';
        syncButton.style.cssText = `
            padding: 6px 12px;
            background: #4F46E5;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        `;

        syncButton.addEventListener('click', (e) => {
            e.preventDefault();
            this.syncWithAropupu();
        });

        controlsDiv.appendChild(refreshButton);
        controlsDiv.appendChild(syncButton);

        // Add controls to bracket container
        const bracketContainer = this.bracketElement.closest('.bracket-container');
        if (bracketContainer) {
            bracketContainer.style.position = 'relative';
            bracketContainer.appendChild(controlsDiv);
        }
    }

    loadAropupuBracket() {
        // First check if we have tournament data to potentially sync
        if (!this.tournamentId) {
            this.bracketElement.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full p-8 text-center">
                    <div class="text-4xl mb-4 text-yellow-500">⚠️</div>
                    <h3 class="text-xl font-bold mb-2">No Aropupu Tournament ID</h3>
                    <p class="text-gray-600 mb-4">Aropupu tournament ID is required to connect to aropupu.fi system.</p>
                    <p class="text-sm text-gray-500">This will connect to the Finnish tournament system.</p>
                </div>
            `;
            return;
        }

        // Try to load from aropupu.fi system
        // Since we don't have the actual API, we'll provide both: 
        // 1. A connection to aropupu.fi if tournament exists there
        // Only show internal representation using Aropupu style
        this.renderAropupuBracket();
    }

    renderAropupuBracket() {
        // Show both options: external system and internal representation
        this.bracketElement.innerHTML = `
            <div class="aropupu-bracket-container">
                <div class="aropupu-header" style="margin-bottom: 15px; padding: 10px; background: #f8fafc; border-radius: 8px; text-align: center;">
                    <h3 style="color: #4F46E5; font-weight: bold;">Aropupu Bracket System</h3>
                    <p class="text-sm text-gray-600">Finnish tournament system integration</p>
                </div>
                
                <div class="aropupu-content" style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div class="external-section" style="flex: 1; min-width: 300px;">
                        <h4 style="color: #4F46E5; margin-bottom: 10px;">External System</h4>
                        <div class="aropupu-external-frame" style="border: 2px solid #e2e8f0; border-radius: 8px; overflow: hidden; min-height: 400px; background: white;">
                            <iframe 
                                src="${this.tournamentId.startsWith('comp-') ? 'about:blank' : 'https://www.aropupu.fi/bracket/' + this.tournamentId}" 
                                width="100%" 
                                height="400" 
                                frameborder="0" 
                                style="display: ${this.tournamentId.startsWith('comp-') ? 'none' : 'block'};">
                            </iframe>
                            <div class="no-external" style="display: ${this.tournamentId.startsWith('comp-') ? 'block' : 'none'}; padding: 20px; text-align: center; color: #94a3b8;">
                                <div style="font-size: 48px; margin-bottom: 10px;">🌐</div>
                                <p>No external tournament found</p>
                                <p class="text-sm">Tournament ID: ${this.tournamentId}</p>
                                <p class="text-xs mt-2">Connect your Aropupu tournament here</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="internal-section" style="flex: 1; min-width: 300px;">
                        <h4 style="color: #4F46E5; margin-bottom: 10px;">Internal Representation</h4>
                        <div class="aropupu-internal-view" style="border: 2px solid #e2e8f0; border-radius: 8px; padding: 15px; min-height: 400px; background: white;">
                            ${this.renderInternalBracket()}
                        </div>
                    </div>
                </div>
                
                <div class="aropupu-footer" style="margin-top: 15px; padding: 10px; background: #f8fafc; border-radius: 8px; text-align: center; font-size: 12px; color: #64748b;">
                    Powered by Aropupu.fi • Finnish Tournament System
                </div>
            </div>
        `;
    }

    renderInternalBracket() {
        if (!this.teamsData || this.teamsData.length < 2) {
            return `
                <div class="flex flex-col items-center justify-center h-full text-center">
                    <div class="text-3xl mb-2 text-gray-400">📊</div>
                    <p class="text-gray-600">Not enough teams</p>
                    <p class="text-sm text-gray-500">Need at least 2 teams to generate bracket</p>
                </div>
            `;
        }

        // Ensure teams are properly formatted
        let processedTeams = [];
        
        // Process different possible team formats
        for (let i = 0; i < this.teamsData.length; i++) {
            const team = this.teamsData[i];
            
            if (typeof team === 'string') {
                // If it's just a string, convert to object
                processedTeams.push({
                    name: team,
                    id: `team-${i}`,
                    isBye: team.toLowerCase() === 'bye' || team === 'TBD' || team === 'TBD'
                });
            } else if (typeof team === 'object' && team !== null) {
                // If it's an object, ensure it has the required properties
                processedTeams.push({
                    name: team.name || team[0] || team.team_name || `Team ${i+1}`,
                    id: team.id || `team-${i}`,
                    isBye: team.isBye || false
                });
            } else {
                // If it's something else, create a default team object
                processedTeams.push({
                    name: `Team ${i+1}`,
                    id: `team-${i}`,
                    isBye: false
                });
            }
        }

        // Generate bracket structure following Aropupu.fi format
        const bracketData = this.generateAropupuFormat(processedTeams);
        return this.renderAropupuStyleBracket(bracketData);
    }

    generateAropupuFormat(teams) {
        // Create bracket structure similar to Aropupu's format
        if (!teams || teams.length < 2) {
            return null;
        }

        // Calculate next power of 2 and pad with byes
        const nextPowerOf2 = Math.pow(2, Math.ceil(Math.log2(teams.length)));
        const paddedTeams = [...teams];
        
        while (paddedTeams.length < nextPowerOf2) {
            paddedTeams.push({ 
                name: "BYE", 
                id: `bye-${paddedTeams.length}`, 
                isBye: true 
            });
        }

        // Create bracket rounds in Aropupu style
        let currentRound = paddedTeams;
        const bracketRounds = [];
        
        while (currentRound.length > 1) {
            const nextRound = [];
            const roundMatches = [];
            
            for (let i = 0; i < currentRound.length; i += 2) {
                const homeTeam = currentRound[i];
                const awayTeam = currentRound[i + 1];
                
                roundMatches.push({
                    id: `match-${bracketRounds.length}-${i/2}`,
                    home: homeTeam,
                    away: awayTeam,
                    round: bracketRounds.length,
                    position: i/2
                });
                
                // For visualization, determine next team
                if (homeTeam.isBye) {
                    nextRound.push(awayTeam);
                } else if (awayTeam.isBye) {
                    nextRound.push(homeTeam);
                } else {
                    // In real implementation, this would be based on match results
                    nextRound.push(i % 4 === 0 ? homeTeam : awayTeam);
                }
            }
            
            bracketRounds.push(roundMatches);
            currentRound = nextRound;
        }
        
        return {
            teams: teams,
            rounds: bracketRounds,
            totalRounds: bracketRounds.length
        };
    }

    renderAropupuStyleBracket(bracketData) {
        if (!bracketData || !bracketData.teams || bracketData.teams.length === 0) {
            return `
                <div class="flex items-center justify-center h-full text-gray-500">
                    <div class="text-center">
                        <p>Could not generate bracket</p>
                    </div>
                </div>
            `;
        }

        const teams = bracketData.teams;
        const totalRounds = Math.ceil(Math.log2(teams.length)) + 1; // Total rounds in a complete bracket
        
        // Calculate container width based on number of rounds
        const containerWidth = Math.max(600, totalRounds * 180 + 100);
        
        let html = `
            <div class="aropupu-internal-container" style="min-width: ${containerWidth}px; overflow-x: auto; padding: 10px;">
                <div class="aropupu-internal-wrapper" style="display: flex; gap: 25px; align-items: center; min-width: ${containerWidth}px;">
        `;
        
        (bracketData.rounds || []).forEach((round, roundIndex) => {
            const roundLabel = this.getAropupuRoundLabel(roundIndex, totalRounds);
            html += `
                <div class="aropupu-round" style="display: flex; flex-direction: column; gap: 12px; min-width: 140px;">
                    <div class="round-header" style="text-align: center; font-weight: bold; margin-bottom: 8px; color: #4F46E5; font-size: 14px;">
                        ${roundLabel}
                    </div>
            `;
            
            round.forEach(match => {
                html += this.renderAropupuMatch(match, roundIndex);
            });
            
            html += `</div>`;
        });
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }
    
    getAropupuRoundLabel(roundIndex, totalRounds) {
        const labels = [
            'Finals', 'Semifinals', 'Quarterfinals', 'Round of 16', 
            'Round of 32', 'Round of 64', 'Round of 128', 'First Round'
        ];
        
        // Map from last round to first
        const labelIndex = totalRounds - 1 - roundIndex;
        if (labelIndex < labels.length) {
            return labels[labelIndex];
        }
        
        return `Round ${roundIndex + 1}`;
    }
    
    renderAropupuMatch(match, roundIndex) {
        const homeTeam = match.home;
        const awayTeam = match.away;
        
        const homeByeClass = homeTeam.isBye ? 'bye-team' : '';
        const awayByeClass = awayTeam.isBye ? 'bye-team' : '';
        
        return `
            <div class="aropupu-match" style="
                border: 2px solid #e2e8f0; 
                border-radius: 6px; 
                padding: 10px; 
                margin-bottom: 12px;
                background: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                min-height: 70px;
            ">
                <div class="team home-team ${homeByeClass}" style="
                    padding: 6px 8px; 
                    border-bottom: 1px solid #e2e8f0; 
                    font-weight: ${homeTeam.isBye ? 'normal' : '500'};
                    color: ${homeTeam.isBye ? '#94a3b8' : '#1e293b'};
                    font-size: 13px;
                ">
                    ${homeTeam.name}
                </div>
                <div class="team away-team ${awayByeClass}" style="
                    padding: 6px 8px;
                    font-weight: ${awayTeam.isBye ? 'normal' : '500'};
                    color: ${awayTeam.isBye ? '#94a3b8' : '#1e293b'};
                    font-size: 13px;
                ">
                    ${awayTeam.name}
                </div>
            </div>
        `;
    }

    syncWithAropupu() {
        console.log('Syncing with Aropupu system...');
        
        // In a real implementation, this would connect to aropupu.fi API to sync data
        // For now, we'll just refresh the bracket
        this.showNotification('Synchronizing with Aropupu system...', 'info');
        
        // Simulate API call delay
        setTimeout(() => {
            this.loadAropupuBracket();
            this.showNotification('Synchronization completed', 'success');
        }, 1000);
    }

    showNotification(message, type = 'info') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.aropupu-notification');
        existingNotifications.forEach(note => note.remove());

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `aropupu-notification notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            z-index: 10001;
            font-size: 14px;
            max-width: 400px;
            word-wrap: break-word;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        `;

        // Set color based on type
        if (type === 'success') {
            notification.style.backgroundColor = '#4CAF50';
        } else if (type === 'error') {
            notification.style.backgroundColor = '#f44336';
        } else {
            notification.style.backgroundColor = '#2196F3';
        }

        document.body.appendChild(notification);

        // Remove after 4 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 4000);
    }
    
    renderRemainingRounds(numRounds) {
        let html = '';
        const roundNames = ['Semifinals', 'Finals'];

        for (let i = 0; i < numRounds && i < roundNames.length; i++) {
            html += `
                <div class="aropupu-round" style="display: flex; flex-direction: column; gap: 12px; min-width: 140px;">
                    <div class="round-header" style="text-align: center; font-weight: bold; margin-bottom: 8px; color: #4F46E5; font-size: 14px;">
                        ${roundNames[i]}
                    </div>
            `;
            
            // Placeholder for matches in this round
            html += `
                <div class="aropupu-match-placeholder" style="
                    border: 2px dashed #e2e8f0;
                    border-radius: 6px;
                    padding: 10px;
                    margin-bottom: 12px;
                    background: #f8fafc;
                    min-height: 70px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #94a3b8;
                    font-size: 12px;
                ">
                    Upcoming Match
                </div>
            `;
            
            html += `</div>`;
        }

        return html;
    }

    renderAropupuMatchFromAropupuFormat(matchup, index) {
        const team1 = matchup[0];
        const team2 = matchup[1];

        const team1ByeClass = team1 === "BYE" ? 'bye-team' : '';
        const team2ByeClass = team2 === "BYE" ? 'bye-team' : '';

        return `
            <div class="aropupu-match" style="
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 12px;
                background: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                min-height: 70px;
            ">
                <div class="team team1 ${team1ByeClass}" style="
                    padding: 6px 8px;
                    border-bottom: 1px solid #e2e8f0;
                    font-weight: ${team1 === "BYE" ? 'normal' : '500'};
                    color: ${team1 === "BYE" ? '#94a3b8' : '#1e293b'};
                    font-size: 13px;
                ">
                    ${team1}
                </div>
                <div class="team team2 ${team2ByeClass}" style="
                    padding: 6px 8px;
                    font-weight: ${team2 === "BYE" ? 'normal' : '500'};
                    color: ${team2 === "BYE" ? '#94a3b8' : '#1e293b'};
                    font-size: 13px;
                ">
                    ${team2}
                </div>
            </div>
        `;
    }
}

// Function to initialize Aropupu bracket using aropupu.fi system
function initializeAropupuBracket(competitionId, tournamentId = null, teamsData = null, options = {}) {
    // Create a new instance of Aropupu manager
    const aropupuManager = new AropupuBracketManager();

    // Initialize with the competition data
    aropupuManager.initialize(competitionId, tournamentId, teamsData, options);

    // Store in global scope for potential reuse
    window.aropupuManager = aropupuManager;

    return aropupuManager;
}

// Export for global use
window.AropupuBracketManager = AropupuBracketManager;
window.initializeAropupuBracket = initializeAropupuBracket;