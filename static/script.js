document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('toggleBtn');
    const calibrateButton = document.getElementById('calibrate-button')

    function pause(){
        let isPaused = false;
        fetch('/toggle_stream', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                isPaused = !isPaused;
                btn.textContent = isPaused ? 'Resume' : 'Pause';
            })
            .catch(err => console.error('Error toggling stream:', err));
    }

    function calibrate(){
        fetch('')
    }
    
    // Example placeholder for another function
    function anotherFeature() {
        console.log("New feature added.");
    }
    
    btn.addEventListener('click', pause);
});
