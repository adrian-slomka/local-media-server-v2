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
        .then(data => {
            console.log(data);
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
            watchlistButton.classList.remove('filled');  // Remove the "filled" class if unliked
        }
    }
});

// Handle click event on the remove button on watchlist page
function submitRemove(remove) {
    const _itemId_ = remove;
    fetch(`/set_user_item_data/${_itemId_}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            watchlistStatus: 0,
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
        location.reload();
    })
    .catch(error => {
        console.log(error);
    });
}