/*
 * Client-side validation for file uploads in Django Admin
 * Limits total upload size to 4MB to prevent Vercel 413 Payload Too Large errors.
 */

document.addEventListener('DOMContentLoaded', function () {
    // Maximum total size in bytes (4MB)
    const MAX_TOTAL_SIZE = 4 * 1024 * 1024;

    // Function to check file sizes
    function checkFileSizes(event) {
        const input = event.target;
        if (input.type !== 'file') return;

        const files = input.files;
        if (!files || files.length === 0) return;

        let totalSize = 0;
        let largeFiles = [];

        // Calculate total size and identify large files
        for (let i = 0; i < files.length; i++) {
            totalSize += files[i].size;

            // Check individual file size (2MB limit suggestion)
            if (files[i].size > 2 * 1024 * 1024) {
                largeFiles.push(files[i].name);
            }
        }

        console.log(`Checking upload: ${files.length} files, Total: ${(totalSize / (1024 * 1024)).toFixed(2)} MB`);

        // Validation: Check total size
        if (totalSize > MAX_TOTAL_SIZE) {
            // Format size for display
            const sizeMB = (totalSize / (1024 * 1024)).toFixed(2);

            // Alert the user
            alert(`⚠️ Upload Limit Exceeded!\n\n` +
                `Total size: ${sizeMB} MB\n` +
                `Limit: 4.00 MB\n\n` +
                `Please select fewer or smaller images to ensure successful upload.`);

            // Clear the input to prevent submission
            input.value = '';

            // Visual feedback (shake effect if possible, or red border)
            input.style.borderColor = 'red';
            setTimeout(() => {
                input.style.borderColor = '';
            }, 3000);

            return;
        }

        // Optional: Warn about individual large files without blocking
        if (largeFiles.length > 0) {
            console.warn(`Large files detected: ${largeFiles.join(', ')}`);
        }
    }

    // Attach listener to a parent container to handle current and future file inputs
    // using event delegation
    document.body.addEventListener('change', function (event) {
        if (event.target && event.target.type === 'file') {
            checkFileSizes(event);
        }
    });

    console.log('Admin Upload Limit Script Loaded: 4MB Max');
});
