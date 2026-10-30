document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('videoFileInput');
    const uploadBtn = document.getElementById('uploadVideoBtn');
    const progressBar = document.getElementById('uploadProgressBar');
    const statusText = document.getElementById('uploadStatus');

    const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks

    async function uploadChunk(chunk, uploadId, chunkIndex, totalChunks, filename) {
        const formData = new FormData();
        formData.append('chunk', chunk);
        formData.append('upload_id', uploadId);
        formData.append('chunk_index', chunkIndex);
        formData.append('total_chunks', totalChunks);
        formData.append('filename', filename);

        const response = await fetch('/upload_chunk', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`Chunk ${chunkIndex + 1} upload failed`);
        }
    }

    async function uploadFileInChunks(file) {
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
        const uploadId = Date.now() + '-' + file.name.replace(/\W/g, '');

        for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
            const start = chunkIndex * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const chunk = file.slice(start, end);

            try {
                await uploadChunk(chunk, uploadId, chunkIndex, totalChunks, file.name);
                const progressPercent = Math.round(((chunkIndex + 1) / totalChunks) * 100);
                progressBar.style.width = progressPercent + '%';
                statusText.textContent = `Uploading: ${progressPercent}%`;
            } catch (error) {
                statusText.textContent = 'Upload failed: ' + error.message;
                uploadBtn.disabled = false;
                return false;
            }
        }

        // Notify server to assemble chunks
        const assembleResponse = await fetch('/assemble_chunks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                upload_id: uploadId,
                filename: file.name,
            }),
        });

        if (!assembleResponse.ok) {
            statusText.textContent = 'Failed to assemble file on server';
            uploadBtn.disabled = false;
            return false;
        }

        statusText.textContent = 'Upload complete!';
        window.location.href = '/'; // Redirect or update as needed
        return true;
    }

    uploadBtn.addEventListener('click', async function(e) {
        e.preventDefault();

        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Please select a video file first');
            return;
        }

        uploadBtn.disabled = true;
        progressBar.style.width = '0%';
        statusText.textContent = 'Starting upload...';

        const file = fileInput.files[0];
        await uploadFileInChunks(file);

        uploadBtn.disabled = false;
    });
});
