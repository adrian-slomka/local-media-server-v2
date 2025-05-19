// Get scroll settings based on screen size
function getScrollSettings() {
    if (window.innerWidth < 600) {
        return { step: 15, maxCount: 15 };  // Small screens (slower, smoother)
    } else if (window.innerWidth < 1024) {
        return { step: 15, maxCount: 25 };  // Tablets (moderate speed)
    } else {
        return { step: 20, maxCount: 80 };  // Large screens (faster)
    }
}

// Function to scroll in a specific section (Recent, Movies, or Series)
function smoothScroll(sectionId, direction) {
    let scroller = document.getElementById(sectionId);
    let { step, maxCount } = getScrollSettings(); // Get values based on screen size
    step *= direction; // Apply direction (-1 for left, 1 for right)
    let count = 0;

    function scrollStep() {
        if (count < maxCount) {
            scroller.scrollBy({ left: step });
            count++;
            requestAnimationFrame(scrollStep);
        }
    }

    scrollStep();
}

// Add event listeners for each scroll button
document.getElementById("scroll-left-recent").addEventListener("click", function () {
    smoothScroll("scroller-recent", -1); // Scroll left in the "recent" section
});

document.getElementById("scroll-right-recent").addEventListener("click", function () {
    smoothScroll("scroller-recent", 1); // Scroll right in the "recent" section
});

document.getElementById("scroll-left-movies").addEventListener("click", function () {
    smoothScroll("scroller-movies", -1); // Scroll left in the "movies" section
});

document.getElementById("scroll-right-movies").addEventListener("click", function () {
    smoothScroll("scroller-movies", 1); // Scroll right in the "movies" section
});

document.getElementById("scroll-left-series").addEventListener("click", function () {
    smoothScroll("scroller-series", -1); // Scroll left in the "series" section
});

document.getElementById("scroll-right-series").addEventListener("click", function () {
    smoothScroll("scroller-series", 1); // Scroll right in the "series" section
});