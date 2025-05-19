document.addEventListener("DOMContentLoaded", function () {
    // Toggle menu
    const drawerMenuButton = document.querySelector('.header-menu');
    const drawerMenuOpen = document.querySelector('.off-screen-drawer-menu')
    // Toggle overlay
    const offScreenMenuOverlay = document.querySelector('.drawer-menu-bg-overlay-open');


    if (drawerMenuButton) {
        drawerMenuButton.addEventListener('click', function () {
            // Toggle the 'active' class on each element to show/hide the menu
            if (drawerMenuOpen) drawerMenuOpen.classList.toggle('active');
            if (offScreenMenuOverlay) offScreenMenuOverlay.classList.toggle('active');
        });
    }
    // Close the menu when clicking on the overlay
    if (offScreenMenuOverlay) {
        offScreenMenuOverlay.addEventListener('click', function () {
            // Remove 'active' class from both menu and overlay to hide them
            if (drawerMenuOpen) drawerMenuOpen.classList.remove('active');
            if (offScreenMenuOverlay) offScreenMenuOverlay.classList.remove('active');
        });
    }
});