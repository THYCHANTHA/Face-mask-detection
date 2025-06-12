document.addEventListener('DOMContentLoaded', function() {
    // File upload functionality
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const previewContainer = document.getElementById('previewContainer');
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');

    // Webcam controls
    const updateSizeBtn = document.getElementById('updateSizeBtn');
    const widthInput = document.getElementById('width');
    const heightInput = document.getElementById('height');
    const webcamFeed = document.getElementById('webcam-feed');

    // Handle file selection
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Update file name display
        fileName.textContent = file.name;

        // Clear previous preview
        previewContainer.innerHTML = '';
        previewContainer.style.display = 'none';

        // Create preview based on file type
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.createElement('img');
                img.src = e.target.result;
                previewContainer.appendChild(img);
                previewContainer.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else if (file.type.startsWith('video/')) {
            const video = document.createElement('video');
            video.controls = true;
            const source = document.createElement('source');
            source.src = URL.createObjectURL(file);
            source.type = file.type;
            video.appendChild(source);
            previewContainer.appendChild(video);
            previewContainer.style.display = 'block';
        }
    });

    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate file was selected
        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Please select a file first');
            return;
        }

        // Show loading state
        submitBtn.disabled = true;
        loadingIndicator.style.display = 'flex';

        // Submit the form
        this.submit();
    });

    // Reset form after submission (if page doesn't reload)
    uploadForm.addEventListener('reset', function() {
        fileName.textContent = 'Choose file';
        previewContainer.innerHTML = '';
        previewContainer.style.display = 'none';
        submitBtn.disabled = false;
        loadingIndicator.style.display = 'none';
    });

    // Webcam size update handler
    if (updateSizeBtn) {
        updateSizeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const width = parseInt(widthInput.value);
            const height = parseInt(heightInput.value);
            
            if (isNaN(width) || isNaN(height) || width < 100 || height < 100) {
                alert('Please enter valid dimensions (minimum 100px)');
                return;
            }

            webcamFeed.src = `{{ url_for('video_feed') }}?width=${width}&height=${height}`;
        });
    }

});



document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const previewContainer = document.getElementById('previewContainer');
    const dropArea = document.getElementById('dropArea');
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');

    // Drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropArea.classList.add('dragover');
    }

    function unhighlight() {
        dropArea.classList.remove('dragover');
    }

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length) {
            fileInput.files = files;
            handleFiles(files);
        }
    }

    // File input change handler
    fileInput.addEventListener('change', function() {
        if (this.files.length) {
            handleFiles(this.files);
        }
    });

    function handleFiles(files) {
        const file = files[0];
        fileName.textContent = file.name;
        
        // Check if file is an image or video
        if (file.type.startsWith('image/')) {
            previewImage(file);
        } else if (file.type.startsWith('video/')) {
            previewVideo(file);
        }
    }

    function previewImage(file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewContainer.innerHTML = '';
            const img = document.createElement('img');
            img.src = e.target.result;
            previewContainer.appendChild(img);
            previewContainer.style.display = 'block';
            
            // Smooth appearance
            setTimeout(() => {
                previewContainer.style.opacity = '1';
            }, 10);
        };
        reader.readAsDataURL(file);
    }

    function previewVideo(file) {
        previewContainer.innerHTML = '';
        const video = document.createElement('video');
        video.controls = true;
        const source = document.createElement('source');
        source.src = URL.createObjectURL(file);
        source.type = file.type;
        video.appendChild(source);
        previewContainer.appendChild(video);
        previewContainer.style.display = 'block';
        
        // Smooth appearance
        setTimeout(() => {
            previewContainer.style.opacity = '1';
        }, 10);
    }

    // Form submission handler
    uploadForm.addEventListener('submit', function(e) {
        if (!fileInput.files.length) {
            e.preventDefault();
            alert('Please select a file first!');
            return;
        }
        
        // Show loading indicator
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>Processing...</span><i class="fas fa-spinner fa-spin"></i>';
        loadingIndicator.style.display = 'flex';
        
        // You can add additional form validation here if needed
    });

    // Add ripple effect to buttons
    function createRipple(event) {
        const button = event.currentTarget;
        const circle = document.createElement("span");
        const diameter = Math.max(button.clientWidth, button.clientHeight);
        const radius = diameter / 2;

        circle.style.width = circle.style.height = `${diameter}px`;
        circle.style.left = `${event.clientX - button.getBoundingClientRect().left - radius}px`;
        circle.style.top = `${event.clientY - button.getBoundingClientRect().top - radius}px`;
        circle.classList.add("ripple");

        const ripple = button.getElementsByClassName("ripple")[0];
        if (ripple) {
            ripple.remove();
        }

        button.appendChild(circle);
    }

    const buttons = document.querySelectorAll(".btn-primary, .btn-secondary");
    buttons.forEach(button => {
        button.addEventListener("click", createRipple);
    });
});