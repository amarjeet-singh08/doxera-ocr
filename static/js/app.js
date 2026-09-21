document.addEventListener('DOMContentLoaded', () => {
    // Handle file drop area styling
    const dropArea = document.querySelector('.file-drop-area');
    const fileInput = document.querySelector('.file-input');
    const fileMsg = document.querySelector('.file-msg');
    const uploadBtn = document.getElementById('uploadBtn');

    if (dropArea && fileInput) {
        fileInput.addEventListener('change', () => {
            const filesCount = fileInput.files.length;
            if (filesCount === 1) {
                fileMsg.textContent = fileInput.files[0].name;
            } else if (filesCount > 1) {
                fileMsg.textContent = `${filesCount} files selected`;
            } else {
                fileMsg.textContent = 'or drag and drop them here';
            }
        });

        // Add loading state to button
        const form = document.getElementById('uploadForm');
        if (form) {
            form.addEventListener('submit', () => {
                if (fileInput.files.length > 0) {
                    uploadBtn.textContent = 'Uploading...';
                    uploadBtn.disabled = true;
                }
            });
        }
    }
    
    // Auto-refresh dashboard if there are pending items
    const hasPending = document.querySelector('.status-pending');
    const isDashboard = window.location.pathname.includes('/dashboard');
    if (hasPending && isDashboard) {
        setTimeout(() => {
            window.location.reload();
        }, 5000); // refresh every 5 seconds if processing
    }
});
