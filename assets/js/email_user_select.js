/**
 * Email User Select Widget
 * 
 * Allows users to add/remove users by email address. Validates emails against the backend
 * and displays selected users as badges. The hidden field contains the comma-separated
 * list of UIDs which is the actual form value.
 */

(function() {
    // Store all widget instances
    const widgets = new Map();

    /**
     * Initialize an email user select widget
     * @param {string} widgetId - The unique ID for this widget
     * @param {string} apiUrl - The API endpoint to search users (default: /api/v2/users/)
     */
    function initWidget(widgetId, apiUrl) {
        const widget = {
            id: widgetId,
            apiUrl: apiUrl || '/api/v2/users/',
            input: document.getElementById(`${widgetId}_input`),
            addBtn: document.getElementById(`${widgetId}_add_btn`),
            badgeList: document.getElementById(`${widgetId}_badges`),
            hiddenField: document.getElementById(`${widgetId}_value`),
            errorDiv: document.getElementById(`${widgetId}_error`)
        };

        if (!widget.input || !widget.addBtn || !widget.badgeList || !widget.hiddenField) {
            console.error(`EmailUserSelect: Missing elements for widget ${widgetId}`);
            return;
        }

        widgets.set(widgetId, widget);

        // Event listeners
        widget.addBtn.addEventListener('click', () => addEmail(widgetId));
        widget.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addEmail(widgetId);
            }
        });
    }

    /**
     * Add a user to the badge list by email
     * @param {string} widgetId - The widget ID
     */
    async function addEmail(widgetId) {
        const widget = widgets.get(widgetId);
        if (!widget) return;

        const email = widget.input.value.trim();
        if (!email) {
            showError(widgetId, _('Please enter an email address'));
            return;
        }

        // Check if user already exists in the list
        if (userExists(widgetId, email)) {
            showError(widgetId, _('User with email "%{email}" is already in the list', { email }));
            widget.input.value = '';
            return;
        }

        try {
            // Find user by email against backend
            const users = await findUserByEmail(widgetId, email);

            if (users.length === 0) {
                showError(widgetId, _('No user found with email "%{email}"', { email }));
                return;
            }

            if (users.length === 1) {
                const user = users[0];
                addBadge(widgetId, user);
            } else {
                // If multiple users found, show error
                const userList = users.map(u => `${u.full_name || u.username} (${u.email})`).join(', ');
                showError(widgetId, _('Multiple users found for email "%{email}": %{users}', { email, users: userList }));
                return;
            }

            // Clear input and hide error
            widget.input.value = '';
            hideError(widgetId);

        } catch (error) {
            showError(widgetId, _('Error validating email: %{error}', { error: error.message }));
        }
    }

    /**
     * Find users by exact email address using the search parameter of the API
     * @param {string} widgetId - The widget ID
     * @param {string} email - The email address to search for
     * @returns {Promise<Object[]>} - The users with this email address
     * @throws {Error} - If the API request fails
     */
    async function findUserByEmail(widgetId, email) {
        const widget = widgets.get(widgetId);

        // Use the search parameter - the API now uses =user__email for exact match
        const response = await fetch(`${widget.apiUrl}?search=${encodeURIComponent(email)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return (await response.json()).results;
    }

    /**
     * Check if a user already exists in the badge list
     * @param {string} widgetId - The widget ID
     * @param {string} email - The email to check
     * @returns {boolean} - True if user exists in the list
     */
    function userExists(widgetId, email) {
        const widget = widgets.get(widgetId);
        if (!widget) return false;

        const badges = widget.badgeList.querySelectorAll('.badge-item');
        for (const badge of badges) {
            if (badge.dataset.email === email) {
                return true;
            }
        }
        return false;
    }

    /**
     * Add a badge to the list
     * @param {string} widgetId - The widget ID
     * @param {Object} user - The user object
     */
    function addBadge(widgetId, user) {
        const widget = widgets.get(widgetId);
        if (!widget) return;

        const displayName = user.full_name || user.username || user.email;

        const parts = [displayName, user.student_id, user.email].filter(Boolean);
        const text = parts.join(', ');

        const li = document.createElement('li');
        li.className = 'list-inline-item badge-item';
        li.dataset.email = String(user.email || '');
        li.dataset.userId = String(user.id); // Store user ID
        
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'aplus-button--secondary aplus-button--sm btn btn-sm btn-secondary';
        button.addEventListener('click', () => window.removeUser(widgetId, String(user.id)));

        const removeSpan = document.createElement('span');
        removeSpan.setAttribute('aria-label', 'Remove');
        removeSpan.textContent = 'x';

        button.append(document.createTextNode(`${text} `), removeSpan);
        li.appendChild(button);


        widget.badgeList.appendChild(li);
        updateHiddenField(widgetId);
        updatePlaceholder(widgetId);
    }

    /**
     * Remove a user from the badge list
     * @param {string} widgetId - The widget ID
     * @param {string} id - The user ID to remove
     */
    window.removeUser = function(widgetId, id) {
        const widget = widgets.get(widgetId);
        if (!widget) return;

        const badge = widget.badgeList.querySelector(`[data-user-id="${id}"]`);
        if (badge) {
            badge.remove();
            updateHiddenField(widgetId);
            updatePlaceholder(widgetId);
        }
    };

    /**
     * Update the hidden field with current user IDs
     * @param {string} widgetId - The widget ID
     */
    function updateHiddenField(widgetId) {
        const widget = widgets.get(widgetId);
        if (!widget) return;

        const userIds = [];
        const badges = widget.badgeList.querySelectorAll('.badge-item');
        
        badges.forEach(badge => {
            const userId = badge.dataset.userId;
            if (userId) {
                userIds.push(userId);
            }
        });

        // Store as comma-separated user IDs
        widget.hiddenField.value = userIds.join(', ');
    }

    /**
     * Show the placeholder text only while no users have been added
     * @param {string} widgetId - The widget ID
     */
    function updatePlaceholder(widgetId) {
        const widget = widgets.get(widgetId);
        if (!widget) return;

        const placeholder = widget.badgeList.querySelector('.badge-placeholder');
        placeholder.hidden = widget.badgeList.querySelector('.badge-item') !== null;
    }

    /**
     * Show error message
     * @param {string} widgetId - The widget ID
     * @param {string} message - Error message to display
     */
    function showError(widgetId, message) {
        const widget = widgets.get(widgetId);
        if (!widget) return;

        widget.errorDiv.textContent = message;
        widget.errorDiv.style.display = 'block';
        
        // Hide error after 5 seconds
        setTimeout(() => {
            hideError(widgetId);
        }, 5000);
    }

    /**
     * Hide error message
     * @param {string} widgetId - The widget ID
     */
    function hideError(widgetId) {
        const widget = widgets.get(widgetId);
        if (!widget) return;

        widget.errorDiv.style.display = 'none';
    }

    // Auto-initialize widgets when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        // Look for all email user select widgets
        document.querySelectorAll('[data-email-user-select]').forEach(element => {
            const widgetId = element.id;
            const apiUrl = element.dataset.apiUrl || '/api/v2/users/';
            initWidget(widgetId, apiUrl);
        });
    });

    // Expose functions globally for inline event handlers
    window.EmailUserSelect = {
        initWidget,
        addEmail,
        removeUser
    };
})();
