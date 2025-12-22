// -- Manejo de arrastrar y soltar archivos -- #
// 01: configuracion inicial de eventos
document.addEventListener('DOMContentLoaded', function () {

    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return;  // si no existe el elemento, salir

    const fileInput =
        document.getElementById('archivo_de_identidad') ||
        document.getElementById('archivoInput');  // obtiene input de archivo

    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');

    if (!fileInput) return;

    const maxSize = 5 * 1024 * 1024;  // 5MB maximo

    // tipos de archivo permitidos desde el input
    const validTypes = fileInput.accept
        .split(',')
        .map(type => type.trim());

    // -- eventos del drop zone -- #
    dropZone.addEventListener('click', () => fileInput.click());  // click abre selector

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);  // maneja archivo seleccionado
        }
    });

    // arrastrar sobre la zona
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');  // añade clase visual
    });

    // salir de la zona
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');  // quita clase visual
    });

    // soltar archivo
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;  // asigna archivos al input
            handleFile(e.dataTransfer.files[0]);  // maneja primer archivo
        }
    });

    // -- funcion para manejar archivos -- #
    // 01: valida y procesa el archivo subido
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

        // muestra vista previa si existe
        if (filePreview) {
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            filePreview.classList.add('show');
        }

        // actualiza contenido del drop zone
        dropZone.innerHTML = `
            <p><strong>${file.name}</strong></p>
            <p>Haz clic o arrastra otro archivo para reemplazar</p>
        `;
    }

    function resetInput() {
        fileInput.value = '';  // limpia el input
        if (filePreview) filePreview.classList.remove('show');  // oculta vista previa
    }

    // formatea tamaño de archivo para mostrar
    function formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
    }
});