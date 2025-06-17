document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('toggleBtn');
    let isPaused = false;

    btn.addEventListener('click', () => {
        fetch('/toggle_stream', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                isPaused = !isPaused;
                btn.textContent = isPaused ? 'Resume' : 'Pause';
            })
            .catch(err => console.error('Error toggling stream:', err));
    });

    // Example placeholder for another function
    function anotherFeature() {
        console.log("New feature added.");
    }
});
