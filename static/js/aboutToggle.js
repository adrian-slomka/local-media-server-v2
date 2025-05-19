document.addEventListener("DOMContentLoaded", function () {
    const tabs = document.querySelectorAll(".detail-items");
    const sections = document.querySelectorAll(".content-section");

    tabs.forEach(tab => {
        tab.addEventListener("click", function () {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove("active"));

            // Add active class to the clicked tab
            this.classList.add("active");

            // Hide all sections
            sections.forEach(section => section.classList.remove("active"));

            // Show the corresponding section
            const target = this.getAttribute("data-target");
            document.querySelector(`.${target}`).classList.add("active");
        });
    });
});