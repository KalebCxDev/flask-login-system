document.addEventListener('DOMContentLoaded', function () {

    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return;

    const fileInput =
        document.getElementById('archivo_de_identidad') ||
        document.getElementById('archivoInput');

    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');

    if (!fileInput) return;

    const maxSize = 5 * 1024 * 1024;

    const validTypes = fileInput.accept
        .split(',')
        .map(type => type.trim());

    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFile(e.dataTransfer.files[0]);
        }
    });

    function handleFile(file) {

        if (file.size > maxSize) {
            alert(`El archivo supera el tamaño máximo permitido.`);
            resetInput();
            return;
        }

        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!validTypes.includes(extension)) {
            alert('Formato de archivo no permitido.');
            resetInput();
            return;
        }

        if (filePreview) {
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            filePreview.classList.add('show');
        }

        dropZone.innerHTML = `
            <p><strong>${file.name}</strong></p>
            <p>Haz clic o arrastra otro archivo para reemplazar</p>
        `;
    }

    function resetInput() {
        fileInput.value = '';
        if (filePreview) filePreview.classList.remove('show');
    }

    function formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
    }
});
