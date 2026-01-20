// Custom bracket team editor that works with both Arōpuku and Gracket implementations
class BracketTeamEditor {
    constructor() {
        this.editMode = false;
        this.competitionId = null;
        this.bracketElement = null;
        this.currentBracketType = 'aropuku'; // Default to Aropuku
    }
    
    initialize() {
        this.competitionId = JSON.parse(document.getElementById('competition-data').textContent);
        
        // Detect which bracket type is currently active
        this.bracketElement = document.querySelector('#aropuku-bracket #bracket-content');
        
        // Check if Arōpuku bracket is active
        if (document.querySelector('#aropuku-bracket').classList.contains('active') || 
            document.querySelector('#aropuku-view').classList.contains('active')) {
            this.currentBracketType = 'aropuku';
            this.bracketElement = document.getElementById('aropuku-bracket');
        } else {
            // Gracket is active
            this.currentBracketType = 'gracket';
            this.bracketElement = document.getElementById('bracket-content');
        }
        
        if (!this.bracketElement) {
            console.error("Bracket element not found");
            return;
        }
        
        console.log(`${this.currentBracketType} bracket element found, initializing editor`);
        
        // Load any previously saved changes from localStorage
        setTimeout(() => {
            this.loadFromLocalStorage();
        }, 1500); // Slightly after bracket renders
        
        // Add edit mode toggle button
        this.addEditModeToggle();
        
        // Set up custom event listeners after bracket has rendered
        setTimeout(() => {
            this.setupCustomEventListeners();
            console.log("Custom event listeners set up");
        }, 1000); // Give bracket more time to render completely
    }
    
    addEditModeToggle() {
        if (!this.bracketElement) return;
        
        // Create an edit mode toggle button
        const editButton = document.createElement('button');
        editButton.id = 'toggle-edit-mode';
        editButton.textContent = 'Edit Bracket Teams';
        editButton.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            padding: 8px 16px;
            background: #4F46E5;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        `;
        
        // Add button to bracket container
        const bracketContainer = this.bracketElement.closest('.bracket-container');
        if (bracketContainer) {
            // Ensure container has relative positioning
            bracketContainer.style.position = 'relative';
            bracketContainer.appendChild(editButton);
            
            // Add event listener to toggle edit mode
            editButton.addEventListener('click', () => {
                this.toggleEditMode();
            });
        }
    }
    
    toggleEditMode() {
        this.editMode = !this.editMode;
        const bracketContainer = this.bracketElement.closest('.bracket-container');
        
        if (this.editMode) {
            // Add visual indicator for edit mode
            bracketContainer.style.outline = '2px solid #10B981';
            document.getElementById('toggle-edit-mode').textContent = 'Editing ON';
            document.getElementById('toggle-edit-mode').style.background = '#10B981';
            document.getElementById('toggle-edit-mode').style.outline = '2px solid #10B981';
        } else {
            bracketContainer.style.outline = '';
            document.getElementById('toggle-edit-mode').textContent = 'Edit Bracket Teams';
            document.getElementById('toggle-edit-mode').style.background = '#4F46E5';
            document.getElementById('toggle-edit-mode').style.outline = 'none';
        }
    }
    
    setupCustomEventListeners() {
        if (!this.bracketElement) return;
        
        // Setup event listeners based on bracket type
        if (this.currentBracketType === 'aropuku') {
            this.setupAropukuEventListeners();
        } else {
            this.setupGracketEventListeners();
        }
    }
    
    setupAropukuEventListeners() {
        // For Arōpuku, team names might be in different elements
        this.bracketElement.addEventListener('click', (e) => {
            if (this.editMode) {
                console.log("Aropuku edit mode on, clicked element:", e.target, "Tag:", e.target.tagName);
                
                // Try to find team name in various possible elements
                let textElement = null;
                let textContent = '';
                
                // Check if clicked element itself has text content
                if (e.target.textContent && e.target.textContent.trim() !== '') {
                    textContent = e.target.textContent.trim();
                    textElement = e.target;
                }
                
                // Look for elements that commonly contain team names in brackets
                if (!textContent) {
                    // Maybe it's a span, div, or other container with team name
                    const possibleElements = ['span', 'div', 'td', 'li'];
                    if (possibleElements.includes(e.target.tagName.toLowerCase())) {
                        textContent = e.target.textContent.trim();
                        textElement = e.target;
                    }
                }
                
                // Traverse up to find containing text
                if (!textContent) {
                    let parent = e.target;
                    while (parent && parent !== this.bracketElement && parent.nodeType === Node.ELEMENT_NODE) {
                        if (parent.textContent && parent.textContent.trim() !== '') {
                            // Check if this looks like a team name (not just numbers or other labels)
                            if (parent.textContent.length > 3 && 
                                !/^\d+$/.test(parent.textContent.trim()) && 
                                !['vs', 'VS', 'v', 'Match', 'Round'].includes(parent.textContent.toUpperCase())) {
                                textContent = parent.textContent.trim();
                                textElement = parent;
                                break;
                            }
                        }
                        parent = parent.parentElement;
                    }
                }
                
                if (textContent && textElement) {
                    // Allow editing for all teams (TBD, BYE, and existing teams)
                    this.openEditPopupForTeam(textElement, textContent);
                } else {
                    console.log("No valid team text element found in Aropuku bracket");
                }
            }
        });
    }
    
    setupGracketEventListeners() {
        // Original Gracket event listener logic
        this.bracketElement.addEventListener('click', (e) => {
            if (this.editMode) {
                console.log("Gracket edit mode on, clicked element:", e.target, "Tag:", e.target.tagName, "Class:", e.target.className);

                // Find the actual text content by traversing up the DOM
                let currentElement = e.target;
                let textElement = null;
                let textContent = '';

                // Look for text in the current element and its children
                if (currentElement.textContent && currentElement.textContent.trim() !== '') {
                    textContent = currentElement.textContent.trim();
                    textElement = currentElement;
                }

                // If no text found, look for containing text element
                if (!textContent) {
                    // Try to find a text element by traversing up
                    let parent = currentElement;
                    while (parent && parent !== this.bracketElement) {
                        if (parent.tagName && (parent.tagName.toLowerCase() === 'text' || parent.tagName.toLowerCase() === 'tspan')) {
                            if (parent.textContent && parent.textContent.trim() !== '') {
                                textContent = parent.textContent.trim();
                                textElement = parent;
                                break;
                            }
                        }
                        parent = parent.parentElement;
                    }
                }

                // Alternative: look for related elements that might contain the team name
                if (!textContent) {
                    // Check if clicked element has related text within it
                    const textElems = e.target.querySelectorAll('text, tspan');
                    if (textElems.length > 0) {
                        const firstText = textElems[0];
                        if (firstText.textContent && firstText.textContent.trim() !== '') {
                            textContent = firstText.textContent.trim();
                            textElement = firstText;
                        }
                    }
                }

                console.log("Final text content found:", textContent, "Element:", textElement);

                if (textContent && textElement) {
                    // Allow editing for all teams (TBD, BYE, and existing teams)
                    this.openEditPopupForTeam(textElement, textContent);
                } else {
                    console.log("No valid text element or content found in Gracket");
                }
            }
        });
    }
    
    openEditPopupForTeam(textElement, currentName) {
        // Get all enrolled teams for this competition (from the initial teams data)
        const teamsDataElement = document.getElementById('teams-data');
        let teamOptions = '';

        if (teamsDataElement) {
            try {
                const teams = JSON.parse(teamsDataElement.textContent);
                teamOptions += `<option value="">Select a team...</option>`;
                // Add BYE and TBD options at the top
                teamOptions += `<option value="BYE" ${currentName === "BYE" ? 'selected' : ''}>BYE (Bye)</option>`;
                teamOptions += `<option value="TBD" ${currentName === "TBD" || currentName.startsWith("TBD") ? 'selected' : ''}>TBD (To Be Determined)</option>`;

                // Add all enrolled teams
                teams.forEach(team => {
                    const selected = team.name === currentName ? 'selected' : '';
                    teamOptions += `<option value="${team.name}" ${selected}>${team.name}</option>`;
                });
            } catch (e) {
                console.error('Error parsing teams data:', e);
                // Fallback to text input if teams data is not available
                teamOptions = `<option value="">Select a team...</option>`;
                // Still add the BYE and TBD options
                teamOptions += `<option value="BYE">BYE (Bye)</option>`;
                teamOptions += `<option value="TBD">TBD (To Be Determined)</option>`;
            }
        } else {
            // If no teams data element, provide default options
            teamOptions += `<option value="">Select a team...</option>`;
            teamOptions += `<option value="BYE">BYE (Bye)</option>`;
            teamOptions += `<option value="TBD">TBD (To Be Determined)</option>`;
        }

        // Create popup overlay
        const popup = document.createElement('div');
        popup.className = 'bracket-team-edit-popup';
        popup.innerHTML = `
            <div class="popup-content">
                <div class="popup-header">
                    <h3>Edit Team</h3>
                    <button class="close-btn" title="Close">&times;</button>
                </div>
                <form class="team-edit-form">
                    <div class="form-group">
                        <label for="teamSelect">Select Team:</label>
                        ${teamOptions ?
                            `<select id="teamSelect" name="teamName" required class="team-select">
                                ${teamOptions}
                            </select>` :
                            `<input type="text" id="teamNameInput" name="teamName" value="${currentName}" required class="team-input">
                            <small class="help-text">Enter the new team name to replace "${currentName}"</small>`}
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="update-btn">Update Team</button>
                        <button type="button" class="cancel-btn">Cancel</button>
                    </div>
                </form>
                <div class="save-info">
                    <small class="help-text text-gray-500 dark:text-gray-400">Changes saved locally in your browser</small>
                </div>
            </div>
        `;

        // Close button functionality
        popup.querySelector('.close-btn').addEventListener('click', () => {
            document.body.removeChild(popup);
        });

        popup.querySelector('.cancel-btn').addEventListener('click', () => {
            document.body.removeChild(popup);
        });

        // Form submission
        popup.querySelector('.team-edit-form').addEventListener('submit', (e) => {
            e.preventDefault();

            let newTeamName;
            const selectElement = popup.querySelector('#teamSelect');
            if (selectElement) {
                newTeamName = selectElement.value;
            } else {
                const inputElement = popup.querySelector('#teamNameInput');
                newTeamName = inputElement.value;
            }

            if (!newTeamName) {
                alert('Please select or enter a team name');
                return;
            }

            // Update the text element based on bracket type
            if (this.currentBracketType === 'aropuku') {
                // For Arōpuku, the update might involve different methods
                textElement.textContent = newTeamName;
                
                // Arōpuku might require special update methods if it uses a complex structure
                // For now, we'll just update the textContent directly
            } else {
                // For Gracket, update the SVG text element
                textElement.textContent = newTeamName;
            }

            // Close popup
            document.body.removeChild(popup);

            // Show local update feedback
            this.showNotification(`Team updated to: ${newTeamName}`, 'success');

            // Call backend to record the change (this is more complex as we don't have position mapping)
            // In a full implementation, you'd have to track which specific match was updated
            this.updateTeamOnBackend(newTeamName, currentName);
        });

        document.body.appendChild(popup);
    }

    updateTeamOnBackend(newTeamName, oldName) {
        // Call Django API to record the team name change
        fetch('/bracket/update-team/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            },
            body: JSON.stringify({
                competition_id: this.competitionId,
                old_team_name: oldName,
                new_team_name: newTeamName,
                change_type: 'name_update'
                // Note: In a real implementation you'd need to map SVG elements to specific Match objects
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Team update recorded successfully');
            } else {
                console.error('Error recording team update:', data.error);
                this.showNotification('Warning: Display updated, but server sync failed', 'error');
            }
        })
        .catch(error => {
            console.error('Network error during team update:', error);
            this.showNotification('Network error: Changes may not be saved', 'error');
        });

        // Also save to local storage for persistence after refresh
        this.saveToLocalStorage(oldName, newTeamName);
    }

    saveToLocalStorage(oldName, newTeamName) {
        try {
            const storageKey = `bracket_teams_${this.competitionId}`;
            let savedChanges = JSON.parse(localStorage.getItem(storageKey)) || {};

            // Update the changes object
            savedChanges[oldName] = newTeamName;

            // Save back to localStorage
            localStorage.setItem(storageKey, JSON.stringify(savedChanges));
        } catch (e) {
            console.error('Error saving to localStorage:', e);
        }
    }

    loadFromLocalStorage() {
        try {
            const storageKey = `bracket_teams_${this.competitionId}`;
            const savedChanges = JSON.parse(localStorage.getItem(storageKey)) || {};

            // Apply saved changes to the current bracket
            this.applySavedChanges(savedChanges);
        } catch (e) {
            console.error('Error loading from localStorage:', e);
        }
    }

    applySavedChanges(changes) {
        if (!changes || Object.keys(changes).length === 0) return;

        // Apply changes based on bracket type
        if (this.currentBracketType === 'aropuku') {
            // For Arōpuku, we need to find elements that contain the old names and update them
            const allTextElements = this.bracketElement.querySelectorAll('*');
            allTextElements.forEach(element => {
                if (element.textContent) {
                    Object.entries(changes).forEach(([oldName, newName]) => {
                        if (element.textContent.trim() === oldName) {
                            element.textContent = newName;
                        }
                    });
                }
            });
        } else {
            // For Gracket, find SVG text elements
            const textElements = this.bracketElement.querySelectorAll('text, span.g_team-name');
            textElements.forEach(textElement => {
                const currentText = textElement.textContent.trim();
                if (changes[currentText]) {
                    textElement.textContent = changes[currentText];
                }
            });
        }
    }

    clearLocalChanges() {
        try {
            const storageKey = `bracket_teams_${this.competitionId}`;
            localStorage.removeItem(storageKey);
            console.log('Local bracket changes cleared');
        } catch (e) {
            console.error('Error clearing localStorage:', e);
        }
    }

    showNotification(message, type = 'info') {
        // Create a simple notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
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

    getCookie(name) {
        // Helper function to get CSRF token
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Add CSS for the popup and edit mode
function addBracketEditorStyles() {
    if (!document.getElementById('bracket-editor-styles')) {
        const style = document.createElement('style');
        style.id = 'bracket-editor-styles';
        style.textContent = `
            .bracket-team-edit-popup {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
            }

            .bracket-team-edit-popup .popup-content {
                background: white;
                padding: 20px;
                border-radius: 8px;
                min-width: 350px;
                max-width: 500px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            }

            .bracket-team-edit-popup .popup-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }

            .bracket-team-edit-popup .popup-header h3 {
                margin: 0;
                color: #374151;
            }

            .bracket-team-edit-popup .close-btn {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                width: 30px;
                height: 30px;
                color: #6b7280;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .bracket-team-edit-popup .close-btn:hover {
                color: #ef4444;
                background: #f9fafb;
                border-radius: 4px;
            }

            .bracket-team-edit-popup .form-group {
                margin-bottom: 15px;
            }

            .bracket-team-edit-popup .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
                color: #374151;
            }

            .bracket-team-edit-popup .form-group input,
            .bracket-team-edit-popup .form-group select {
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                font-size: 14px;
                background-color: white;
                color: #374151;
            }

            .bracket-team-edit-popup .form-group input:focus,
            .bracket-team-edit-popup .form-group select:focus {
                outline: none;
                border-color: #4f46e5;
                box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
            }

            /* Dark mode styles */
            .dark .bracket-team-edit-popup .form-group input,
            .dark .bracket-team-edit-popup .form-group select {
                background-color: #374151; /* gray-700 */
                color: #f9fafb; /* gray-50 */
                border-color: #4b5563; /* gray-600 */
            }

            .bracket-team-edit-popup .form-group option[value="BYE"] {
                font-weight: bold;
                color: #10b981; /* emerald-500 */
                background-color: #ecfdf5; /* emerald-50 */
            }

            .bracket-team-edit-popup .form-group option[value="TBD"] {
                font-weight: bold;
                color: #f59e0b; /* amber-500 */
                background-color: #fffbeb; /* amber-50 */
            }

            /* Dark mode for special options */
            .dark .bracket-team-edit-popup .form-group option[value="BYE"] {
                color: #6ee7b7; /* emerald-300 */
                background-color: #115e59; /* emerald-800 */
            }

            .dark .bracket-team-edit-popup .form-group option[value="TBD"] {
                color: #fcd34d; /* amber-300 */
                background-color: #92400e; /* amber-800 */
            }

            .bracket-team-edit-popup .help-text {
                display: block;
                color: #6b7280;
                font-size: 12px;
                margin-top: 5px;
            }

            .dark .bracket-team-edit-popup .help-text {
                color: #9ca3af; /* gray-400 */
            }

            .bracket-team-edit-popup .save-info {
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px solid #e5e7eb;
                text-align: center;
            }

            .dark .bracket-team-edit-popup .save-info {
                border-top: 1px solid #4b5563;
            }

            .bracket-team-edit-popup .form-actions {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                margin-top: 20px;
                padding-top: 15px;
                border-top: 1px solid #eee;
            }

            .bracket-team-edit-popup .form-actions button {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
            }

            .bracket-team-edit-popup .form-actions .cancel-btn {
                background: #f3f4f6;
                color: #374151;
            }

            .bracket-team-edit-popup .form-actions .cancel-btn:hover {
                background: #e5e7eb;
            }

            .bracket-team-edit-popup .form-actions .update-btn {
                background: #4F46E5;
                color: white;
            }

            .bracket-team-edit-popup .form-actions .update-btn:hover {
                background: #4338CA;
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize the editor after DOM is ready and bracket has had time to render
document.addEventListener('DOMContentLoaded', function() {
    addBracketEditorStyles();

    // We initialize the editor from the template after bracket renders
    // so we don't need to initialize here
});

// Export for global use
window.BracketTeamEditor = BracketTeamEditor;