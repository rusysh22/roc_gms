// Optimized bracket viewer implementation
function initializeBracketViewer() {
    // Check if we're on the seeding page (no matches exist yet)
    const hasMatches = $('.bracket-container').length > 0 && $('#teams-data').length > 0 && $('#matches-data').length > 0;
    
    // Initialize seeding functionality if we're on the seeding page (no matches yet)
    // This happens when competition.matches.exists is false in the template
    if (!$('#bracket-section').length) {
        initializeSeeding();
    }
    // If on bracket page with matches, the bracket toggle functionality will be handled by template script
}

$(document).ready(function() {
    initializeBracketViewer();
});

// Handle HTMX swap events if present
document.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target.id === 'bracket-content') {
        setTimeout(initializeBracketViewer, 300);
    }
});

function initializeSeeding() {
    const seedingListEl = document.getElementById('seeding-list');
    const pairingsContainer = $('#visual-pairings-container');

    if (seedingListEl) {
        function updateVisualPairings() {
            const items = Array.from(seedingListEl.querySelectorAll('.seed-item'));
            const teams = items.map((item, index) => ({
                id: item.dataset.id,
                name: item.querySelector('.seed-name').textContent,
                originalIndex: index + 1
            }));

            pairingsContainer.empty();

            const numTeams = teams.length;
            if (numTeams === 0) return;

            let matchNumber = 1;

            for (let i = 0; i < numTeams; i += 2) {
                const team1 = teams[i];
                const team2 = (i + 1 < numTeams) ? teams[i + 1] : null;

                if (team2) {
                    // It's a match
                    const matchBox = `
                        <div class="match-pairing-box">
                            <div class="match-pairing-header">Match ${matchNumber}</div>
                            <div class="match-pairing-body">
                                <div class="paired-team">
                                    <span class="seed-name">${team1.name}</span>
                                    <span class="seed-number">#${team1.originalIndex}</span>
                                </div>
                                <div class="vs-divider">vs</div>
                                <div class="paired-team">
                                    <span class="seed-name">${team2.name}</span>
                                    <span class="seed-number">#${team2.originalIndex}</span>
                                </div>
                            </div>
                        </div>
                    `;
                    pairingsContainer.append(matchBox);
                    matchNumber++;
                } else {
                    // It's a bye for the last team
                    const byeBox = `
                        <div class="match-pairing-box bye-box">
                            <div class="match-pairing-body">
                                <div class="paired-team">
                                    <span class="seed-name">${team1.name}</span>
                                    <span class="seed-number">#${team1.originalIndex}</span>
                                </div>
                                <div class="vs-divider">BYE</div>
                            </div>
                        </div>
                    `;
                    pairingsContainer.append(byeBox);
                }
            }
        }

        const sortable = new Sortable(seedingListEl, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            onUpdate: function (evt) {
                // Re-number the draggable list
                $(seedingListEl).children().each(function(index) {
                    $(this).find('.seed-number').text('#' + (index + 1));
                });
                // Update the visual pairings on the right
                updateVisualPairings();
            }
        });

        // Initial render
        updateVisualPairings();

        $('#save-seeding-btn').on('click', function() {
            const btn = $(this);
            btn.prop('disabled', true).text('Saving...');
            const orderedTeamIds = sortable.toArray();
            $.ajax({
                url: `/bracket/save-seeding/${getCompetitionId()}/`,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ ordered_ids: orderedTeamIds }),
                headers: { 'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val() },
                success: function(response) {
                    if (response.success) {
                        window.location.reload();
                    } else {
                        alert('Error: ' + response.error);
                        btn.prop('disabled', false).text('💾 Simpan Urutan & Buat Bracket');
                    }
                },
                error: function() {
                    alert('An unknown error occurred.');
                    btn.prop('disabled', false).text('💾 Simpan Urutan & Buat Bracket');
                }
            });
        });
    }
}

function getCompetitionId() {
    // Try to get competition ID from URL
    const pathParts = window.location.pathname.split('/');
    const bracketIndex = pathParts.indexOf('bracket');
    if (bracketIndex !== -1 && bracketIndex + 1 < pathParts.length) {
        return pathParts[bracketIndex + 1];
    }
    
    // Try to get from data attribute on page
    const bracketSection = document.getElementById('bracket-section');
    if (bracketSection && bracketSection.dataset.competitionId) {
        return bracketSection.dataset.competitionId;
    }
    
    // Try to get from bracket content element
    const bracketContent = document.getElementById('bracket-content');
    if (bracketContent && bracketContent.dataset.competitionId) {
        return bracketContent.dataset.competitionId;
    }
    
    // Try to get from seeding section
    const seedingSection = document.getElementById('seeding-section');
    if (seedingSection && seedingSection.dataset.competitionId) {
        return seedingSection.dataset.competitionId;
    }
    
    console.error('Could not determine competition ID');
    return null;
}

// This function is kept for backward compatibility but not actively used
// with the new multi-system bracket in template
function renderGracketForTemplate(matches, teams, container) {
    if (matches.length === 0) {
        container.html('<p class="text-white">No matches generated yet.</p>');
        return;
    }

    // Create bracket structure for the local Gracket plugin
    const gracketData = [];

    // Group matches by round
    const matchesByRound = {};
    matches.forEach(match => {
        const round = match.round_number || 1;
        if (!matchesByRound[round]) {
            matchesByRound[round] = [];
        }
        matchesByRound[round].push(match);
    });

    // Sort rounds and process each round
    const sortedRounds = Object.keys(matchesByRound).sort((a, b) => parseInt(a) - parseInt(b));

    sortedRounds.forEach(roundNumber => {
        const roundMatches = matchesByRound[roundNumber];
        const roundGames = [];

        // Process each match in this round
        roundMatches.forEach(match => {
            // Create teams for this game
            const team1 = {
                name: match.home_team_name || 'TBD',
                seed: 0, // Use appropriate seeding if available
                score: match.home_score !== null ? match.home_score : 0
            };

            const team2 = {
                name: match.away_team_name || 'TBD',
                seed: 0, // Use appropriate seeding if available
                score: match.away_score !== null ? match.away_score : 0
            };

            roundGames.push([team1, team2]);
        });

        gracketData.push(roundGames);
    });

    // Create the Gracket container
    const gracketContainer = $('<div class="my_gracket" style="min-height: 500px;"></div>');
    container.html('').append(gracketContainer);

    try {
        // Initialize the local Gracket plugin
        gracketContainer.gracket({
            src: gracketData,
            roundLabels: sortedRounds.map((round, index) => {
                const totalRounds = sortedRounds.length;
                if (totalRounds === 1) return 'Round';
                if (round === Math.max(...sortedRounds)) return 'Final';
                if (round === Math.max(...sortedRounds) - 1) return 'Semi-Final';
                if (round === Math.max(...sortedRounds) - 2) return 'Quarter-Final';
                return `Round ${round}`;
            })
        });
    } catch (error) {
        console.error('Gracket error:', error);
        container.html('<p class="text-white">Error rendering Gracket: ' + error.message + '</p>');
    }
}