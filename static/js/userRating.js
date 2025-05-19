document.addEventListener("DOMContentLoaded", function () {
    const stars = document.querySelectorAll(".rating-stars");
    const ratingButtons = document.querySelectorAll(".detail-button-container");

    const itemId = document.querySelector('.rating-star-buttons').getAttribute('data-item-id');

    // Fetch the user rating from the backend database
    fetch(`/get_user_item_data/${itemId}`)
        .then(response => response.json())
        .then(data => {
            if (data.rating) {
                // Apply the rating from the database to the stars
                fillStars(parseInt(data.rating));
            }
        })
        .catch(error => {
            console.log(error);
        });

    // Handle hover effect on the stars
    ratingButtons.forEach((button, index) => {
        button.addEventListener("mouseover", () => {
            // Highlight all stars up to the hovered one
            stars.forEach((star, i) => {
                if (i <= index) {
                    star.classList.add("hovered");
                } else {
                    star.classList.remove("hovered");
                }
            });
        });

        // Remove hover effect when the mouse leaves the container
        button.addEventListener("mouseout", () => {
            stars.forEach(star => {
                star.classList.remove("hovered");
            });
        });

        // Fill the stars when clicked
        button.addEventListener("click", () => {
            const ratingValue = index + 1;

            // Immediately update the stars without waiting for a response
            fillStars(ratingValue);

            // Send the new rating to the backend
            fetch(`/set_user_item_data/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ rating: ratingValue })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('rating updated.');
                }
            })
            .catch(error => {
                console.log(error);
            });
        });
    });

    // Function to fill stars based on the rating
    function fillStars(rating) {
        stars.forEach((star, i) => {
            if (i < rating) {
                star.classList.add("filled");
            } else {
                star.classList.remove("filled");
            }
        });
    }
});

function submitRating(rating) {
    const itemId = document.querySelector('.rating-star-buttons').getAttribute('data-item-id');
    
    fetch(`/set_user_item_data/${itemId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            rating: rating,
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
    })
    .catch(error => {
        console.error(error);
    });
}