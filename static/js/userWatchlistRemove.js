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