document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById("video");
    const itemId = document.querySelector('.video-player-wrapper').getAttribute('item-id');
    const metadataId = document.querySelector('.video-player-wrapper').getAttribute('metadata-id');
    const startTime = document.querySelector('.video-player-wrapper').getAttribute('data-start-time');
    let lastSentTime  = 0
    let startTimeSet = false;  // Flag to prevent multiple seeks


    video.addEventListener('play', () => {
        if (startTime > 0 && !startTimeSet) {
            // Attempt to set the start time. If it fails, wait for canplay.
            try {
                video.currentTime = startTime;
                startTimeSet = true;
            } catch (e) {
                console.warn('Seeking failed, waiting for canplay...');
            }
        }
    });

    video.addEventListener('canplay', () => {
        if (startTime > 0 && !startTimeSet) {
            video.currentTime = startTime;
            startTimeSet = true;
        }
    });

    setInterval(() => {
        if (!video.paused && !video.ended) {
            currentTime = Math.floor(video.currentTime);
            // Only send if currentTime has changed
            if (currentTime !== lastSentTime) {
                sendWatchtime(currentTime);
                lastSentTime = currentTime;
            }
        }
    }, 5000);

    const sendWatchtime = () => {
        fetch('/update_watchtime', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ item_id: itemId, metadata_id: metadataId, currentTime: currentTime, videoDuration: video.duration})
        }).catch(err => console.log('Error sending watchtime data:', err));
    };

    // Send data on video end
    video.addEventListener('onended', sendWatchtime);
});