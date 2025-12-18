document.addEventListener('DOMContentLoaded', function () {

    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return; // Si no hay dropZone, no hacer nada

    // Detectar qué input file existe
    const fileInput =
        document.getElementById('archivo_de_identidad') ||
        document.getElementById('archivoInput');

    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');

    if (!fileInput) return;

    // Tamaño máximo según el formulario
    const maxSize = fileInput.id === 'archivo_de_identidad'
        ? 5 * 1024 * 1024   // 5MB Registro
        : 10 * 1024 * 1024; // 10MB Mis archivos

    // Tipos permitidos según input
    const validTypes = fileInput.accept
        .split(',')
        .map(type => type.trim());

    // Click en la zona de drop
    dropZone.addEventListener('click', () => fileInput.click());

    // Cambio de archivo
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag over
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    // Drag leave
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    // Drop
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFile(e.dataTransfer.files[0]);
        }
    });

    function handleFile(file) {

        // Validar tamaño
        if (file.size > maxSize) {
            alert(`El archivo supera el tamaño máximo permitido.`);
            resetInput();
            return;
        }

        // Validar extensión (por accept)
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!validTypes.includes(extension)) {
            alert('Formato de archivo no permitido.');
            resetInput();
            return;
        }

        // Mostrar preview
        if (filePreview) {
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            filePreview.classList.add('show');
        }

        // Actualizar texto del dropzone
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
