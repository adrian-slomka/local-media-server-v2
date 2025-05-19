let debounceTimer;
function searchFunction() {
    var query = document.getElementById("search").value;

    // Clear the previous timeout to prevent multiple AJAX requests
    clearTimeout(debounceTimer);

    // Set the timeout for the next request after the user stops typing
    debounceTimer = setTimeout(function() {
        if (query.length > 0) {
            // Send an AJAX request to fetch search results from the Flask backend
            fetch('/search/results?query=' + encodeURIComponent(query))
                .then(response => response.json())
                .then(data => {
                    var resultsContainer = document.getElementById("results");
                    resultsContainer.innerHTML = '';  // Clear previous results

                    if (data.results.length > 0) {
                        let resultsHTML = '<div class="results-content-header"><h2>Results for "' + query + '":</h2></div><div class="results-content">';
                        data.results.forEach(result => {
                            let resultUrl = "/0/TITLE";
                            resultUrl = resultUrl.replace('0', result.id).replace('TITLE', result.title);

                            let filename = 'static/images/posters/w400_' + result.poster_path.replace('/', '');
                            let imgUrl = 'static/images/default_poster.jpg'
                            imgUrl = imgUrl.replace('static/images/default_poster.jpg', filename)

                            // Handle genres: map and join them with ' | '
                            let genresHTML = result.genres.map((genre, index) => {
                                if (index < result.genres.length - 1) {
                                    return genre + ' | ';  // Add separator for all but the last genre
                                }
                                return genre;  // No separator for the last genre
                            }).join('');  // Join all the genres together

                            resultsHTML += `
                                <a class="card" href="${resultUrl}">
                                    <img class="card-poster poster" src="${imgUrl}"></img>
                                    <div class="card-info">
                                        <div class="card-text card-title search-title" title="${result.title}">${result.title}</div>
                                        <div class="card-text card-description">${genresHTML}</div>
                                    </div>
                                </a>
                        `;
                        });
                        resultsHTML += '</div>';

                        resultsContainer.innerHTML = resultsHTML;
                    } else {
                        // If no results, display a no results message
                        resultsContainer.innerHTML = '<p>No results found for "' + query + '"</p>';
                    }
                })
                .catch(error => console.error('Error fetching search results:', error));
        } else {
            // If the query is empty, clear the results section
            document.getElementById("results").innerHTML = '';
        }
    }, 500);  // Delay in milliseconds before the AJAX request is sent
}