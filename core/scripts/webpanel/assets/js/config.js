document.addEventListener('DOMContentLoaded', function () {
    const mainContent = document.getElementById('config-container');
    const GET_FILE_URL = mainContent.dataset.getFileUrl;
    const SET_FILE_URL = mainContent.dataset.setFileUrl;

    const saveButton = document.getElementById("save-button");
    const restoreButton = document.getElementById("restore-button");
    const container = document.getElementById("jsoneditor");

    const editor = new JSONEditor(container, {
        mode: "code",
        onChange: validateJson
    });

    function validateJson() {
        try {
            editor.get();
            updateSaveButton(true);
            hideErrorMessage();
        } catch (error) {
            updateSaveButton(false);
            showErrorMessage("Invalid JSON! Please correct the errors.");
        }
    }

    function updateSaveButton(isValid) {
        saveButton.disabled = !isValid;
        saveButton.style.cursor = isValid ? "pointer" : "not-allowed";
        saveButton.style.setProperty('background-color', isValid ? "#28a745" : "#ccc", 'important');
        saveButton.style.setProperty('color', isValid ? "#fff" : "#666", 'important');
    }

    function showErrorMessage(message) {
        Swal.fire({
            title: "Error",
            text: message,
            icon: "error",
            showConfirmButton: false,
            timer: 5000,
            position: 'top-right',
            toast: true,
            showClass: { popup: 'animate__animated animate__fadeInDown' },
            hideClass: { popup: 'animate__animated animate__fadeOutUp' }
        });
    }

    function hideErrorMessage() {
        Swal.close();
    }

    function saveJson() {
        Swal.fire({
            title: 'Are you sure?',
            text: 'Do you want to save the changes?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, save it!',
            cancelButtonText: 'Cancel',
            reverseButtons: true
        }).then((result) => {
            if (result.isConfirmed) {
                fetch(SET_FILE_URL, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(editor.get())
                })
                .then(() => {
                    Swal.fire('Saved!', 'Your changes have been saved.', 'success');
                })
                .catch(error => {
                    Swal.fire('Error!', 'There was an error saving your data.', 'error');
                    console.error("Error saving JSON:", error);
                });
            }
        });
    }

    function restoreJson() {
        if (!GET_FILE_URL) return;
        fetch(GET_FILE_URL)
            .then(response => {
                if (!response.ok) throw new Error('File not found or empty');
                // Check if response has content
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.indexOf("application/json") !== -1) {
                    return response.json();
                } else {
                    return response.text().then(text => text ? JSON.parse(text) : {});
                }
            })
            .then(json => {
                editor.set(json || {});
                Swal.fire('Success!', 'Your JSON has been loaded.', 'success');
            })
            .catch(error => {
                console.warn("Failed to load JSON, defaulting to empty:", error);
                editor.set({});
                Swal.fire({
                    icon: 'info',
                    title: 'New Config',
                    text: 'Loaded empty configuration.',
                    timer: 2000
                });
            });
    }

    saveButton.addEventListener('click', saveJson);
    restoreButton.addEventListener('click', restoreJson);

    restoreJson();
});