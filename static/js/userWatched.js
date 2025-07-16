const mediaItemId = document.querySelector('.card-detail-item').getAttribute('item-id');

// Fetch the watched status for the media item
fetch(`/get_user_item_data_details/${mediaItemId}`)
    .then(response => response.json())
    .then(data => {
        // Check if there is any data returned
        if (data.watched && data.metadata_item_ids) {
            // Iterate over the returned arrays and update button states
            data.metadata_item_ids.forEach((metadataItemId, index) => {
                const watchedStatus = data.watched[index];
                const button = document.querySelector(`.button-highlights-id-${metadataItemId}`);
                
                // If watched status is 1, mark the button as filled, otherwise remove the filled class
                if (button) { // check if .button-highlights-id-${metadataItemId} exist to avoid potential TypeError: button is null
                    if (watchedStatus === 1) {
                        button.classList.add('filled');
                    } else {
                        button.classList.remove('filled');
                    }
                }

            });
        }
    })
    .catch(error => {
        console.log('Error:', error);
    });

// Function to toggle the watched status when a button is clicked
function submitWatched(metadata_item_id) {
    const watchedButton = document.querySelector(`.button-highlights-id-${metadata_item_id}`);
    const newWatchedStatus = watchedButton.classList.contains('filled') ? 0 : 1;
    
    // Send the updated status to the backend
    fetch('/set_user_item_data_details', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            watched: newWatchedStatus,
            metadata_id: metadata_item_id,
            item_id: mediaItemId  
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Response from server:', data); // Debug
        updateButton(newWatchedStatus, metadata_item_id);
    })
    .catch(error => {
        console.log('Error:', error);
    });
}

// Function to update button appearance based on new watched status
function updateButton(newWatchedStatus, metadata_item_id) {
    const button = document.querySelector(`.button-highlights-id-${metadata_item_id}`);
    
    if (newWatchedStatus === 1) {
        button.classList.add('filled');
    } else {
        button.classList.remove('filled');
    }
}