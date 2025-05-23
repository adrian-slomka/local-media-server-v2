document.addEventListener("DOMContentLoaded", function () {
    
const watchlistButton = document.querySelector(".button-liked");
const itemId = document.querySelector('.detail-action-buttons').getAttribute('data-item-id');

// Fetch the user watchlistStatus
fetch(`/get_user_item_data/${itemId}`)
    .then(response => response.json())
    .then(data => {
        if (data.watchlistStatus !== undefined) {
            updateWatchlistButton(data.watchlistStatus); // Apply the initial watchlistStatus status to the button
        }
    })
    .catch(error => {
        console.log(error);
    });

// Handle click event on the watchlist button
watchlistButton.addEventListener("click", () => {
    const newWatchlistStatus = watchlistButton.classList.contains('filled') ? 0 : 1;
    fetch(`/set_user_item_data/${itemId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            watchlistStatus: newWatchlistStatus
        })
    })
    .then(response => response.json())
    .then(() => {
        updateWatchlistButton(newWatchlistStatus); 
    })
    .catch(error => {
        console.log(error);
    });
});

// Function to visually update the liked button based on the status
function updateWatchlistButton(watchlistStatus) {
    if (watchlistStatus === 1) {
        watchlistButton.classList.add('filled');
    } else {
        watchlistButton.classList.remove('filled');
    }
}
});