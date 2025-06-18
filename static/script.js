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
        fetch('/calibrate', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            console.log('Data reset:', data.status);
        })
        .catch(err => console.error('Reset error:', err));
    }
    
    btn.addEventListener('click', pause);
    calibrateButton.addEventListener('click', calibrate)
});
