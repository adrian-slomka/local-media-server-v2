// Function to fetch settings.json and update the SVG color
async function updateSVGColor() {
    try {
        const response = await fetch('/static/settings.json');
        const settings = await response.json();
        const value = settings.api_updates_auto;

        const svgCircle = document.querySelector('.settings-switch svg circle');
        if (!svgCircle) return;

        svgCircle.setAttribute('fill', value === 1 ? 'green' : 'red');

    } catch (error) {
        console.error('Error fetching settings.json:', error);
    }
}
document.addEventListener('DOMContentLoaded', updateSVGColor);