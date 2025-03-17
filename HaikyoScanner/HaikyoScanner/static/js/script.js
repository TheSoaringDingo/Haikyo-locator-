document.addEventListener('DOMContentLoaded', function() {
    // Handle search form submission
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchTerm = document.getElementById('search-term').value.trim();
            const maxLocations = document.getElementById('max-locations').value;
            
            if (!searchTerm) {
                alert('Please enter a search term or URL');
                return;
            }
            
            // Show loading indicator
            document.querySelector('.search-section').style.display = 'none';
            document.querySelector('.instructions').style.display = 'none';
            document.querySelector('.loading-section').style.display = 'block';
            
            // Reset progress bar
            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');
            const currentStatus = document.getElementById('current-status');
            progressBar.style.width = '0%';
            progressText.textContent = '0%';
            currentStatus.textContent = 'Initializing search...';
            
            // Start progress polling
            let progressInterval = startProgressPolling();
            
            // Submit search request
            fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `search_term=${encodeURIComponent(searchTerm)}&max_locations=${encodeURIComponent(maxLocations)}`
            })
            .then(response => response.json())
            .then(data => {
                // Clear progress polling
                clearInterval(progressInterval);
                
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    // Hide loading indicator and show search form again
                    document.querySelector('.loading-section').style.display = 'none';
                    document.querySelector('.search-section').style.display = 'block';
                    document.querySelector('.instructions').style.display = 'block';
                    return;
                }
                
                // Set progress to 100% before redirecting
                progressBar.style.width = '100%';
                progressText.textContent = '100%';
                currentStatus.textContent = 'Search complete! Redirecting to results...';
                
                // Redirect to map page after a short delay
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 500);
            })
            .catch(error => {
                // Clear progress polling
                clearInterval(progressInterval);
                
                console.error('Error:', error);
                alert('An error occurred while processing your request. Please try again.');
                // Hide loading indicator and show search form again
                document.querySelector('.loading-section').style.display = 'none';
                document.querySelector('.search-section').style.display = 'block';
                document.querySelector('.instructions').style.display = 'block';
            });
        });
    }
    
    // Function to poll progress
    function startProgressPolling() {
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        const currentStatus = document.getElementById('current-status');
        
        return setInterval(() => {
            fetch('/progress')
            .then(response => response.json())
            .then(data => {
                if (data.progress) {
                    const progress = Math.min(data.progress, 100);
                    progressBar.style.width = `${progress}%`;
                    progressText.textContent = `${Math.round(progress)}%`;
                    
                    if (data.current_step) {
                        currentStatus.textContent = data.current_step;
                    }
                }
            })
            .catch(error => {
                console.error('Error polling progress:', error);
            });
        }, 1000);
    }
    
    // Handle search tag clicks
    const searchTags = document.querySelectorAll('.search-tag');
    searchTags.forEach(tag => {
        tag.addEventListener('click', function(e) {
            e.preventDefault();
            const searchTerm = this.getAttribute('data-search');
            document.getElementById('search-term').value = searchTerm;
            // Trigger form submission
            document.getElementById('search-form').dispatchEvent(new Event('submit'));
        });
    });
    
    // Handle export button
    const exportBtn = document.getElementById('export-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            fetch('/export')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                
                // Create a JSON download
                const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
                const downloadAnchor = document.createElement('a');
                downloadAnchor.setAttribute("href", dataStr);
                downloadAnchor.setAttribute("download", "haikyo_locations.json");
                document.body.appendChild(downloadAnchor);
                downloadAnchor.click();
                downloadAnchor.remove();
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while exporting data. Please try again.');
            });
        });
    }
});
