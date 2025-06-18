document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('toggleBtn');
    const calibrateButton = document.getElementById('calibrate-button');
    const imgAlter = document.getElementById('img-alter');
    const img = document.getElementById('frames')
    let showVideo = true
    let isPaused = false;

    function videoToggle(show=true, replacement=""){
        showVideo = show
        if (showVideo){
            img.style.display = 'block'
            imgAlter.style.display = 'none'
        } else {
            img.style.display = 'none'
            imgAlter.innerHTML = replacement
            imgAlter.style.display = 'block'
        }
    }

    function pause(){
        fetch('/toggle_stream', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            videoToggle(isPaused, "<h1>paused</h1>")
            isPaused = !isPaused;
            btn.textContent = isPaused ? 'Resume' : 'Pause';
        })
        .catch(err => console.error('Error toggling stream:', err));

        // to hide the webcam feed
    }

    function calibrate(){
        // pausing the video a bit
        timeLeft = 3;
        // videoToggle(false)
        // imgAlter.textContent = "tutup mata dalam:"

        const timer = setInterval(() => {
            if (timeLeft <= 0) {
                clearInterval(timer);
                imgAlter.innerHTML = "<h1>Time's up!</h1>"
                // imgAlter.textContent = "Time's up!";
                setTimeout(()=>{
                    // the fetch method who're actually sending calibration request.
                    fetch('/calibrate', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if (isPaused){
                            pause()
                        }
                        videoToggle(true)
                        console.log('Data reset:', data.status);
                    })
                    .catch(err => console.error('Reset error:', err));
                }, 1000)
            } else {
                videoToggle(false, `<h1>tutup mata dalam: ${timeLeft}</h1>`)
                // imgAlter.innerHTML = `<h1>tutup mata dalam: ${timeLeft}</h1>`;
                timeLeft -= 1;
            }
        }, 1000);
    }
    
    btn.addEventListener('click', pause);
    calibrateButton.addEventListener('click', calibrate)
});
