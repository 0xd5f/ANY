$(document).ready(function () {
    const contentSection = document.querySelector('.content');

    const API_URLS = {
        getPort: contentSection.dataset.getPortUrl,
        getSni: contentSection.dataset.getSniUrl,
        checkObfs: contentSection.dataset.checkObfsUrl,
        enableObfs: contentSection.dataset.enableObfsUrl,
        disableObfs: contentSection.dataset.disableObfsUrl,
        checkMasquerade: contentSection.dataset.checkMasqueradeUrl,
        enableMasquerade: contentSection.dataset.enableMasqueradeUrl,
        disableMasquerade: contentSection.dataset.disableMasqueradeUrl,
        setPortTemplate: contentSection.dataset.setPortUrlTemplate,
        setSniTemplate: contentSection.dataset.setSniUrlTemplate,
        updateGeoTemplate: contentSection.dataset.updateGeoUrlTemplate
    };

    function isValidDomain(domain) {
        if (!domain) return false;
        const lowerDomain = domain.toLowerCase();
        return !lowerDomain.startsWith("http://") && !lowerDomain.startsWith("https://");
    }

    function isValidPort(port) {
        if (!port) return false;
        return /^[0-9]+$/.test(port) && parseInt(port) > 0 && parseInt(port) <= 65535;
    }

    function confirmAction(title, text, callback) {
        Swal.fire({
            title: title,
            text: text,
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#3085d6",
            cancelButtonColor: "#d33",
            confirmButtonText: "Yes, proceed!",
            cancelButtonText: "Cancel"
        }).then((result) => {
            if (result.isConfirmed) {
                callback();
            }
        });
    }

    function sendRequest(url, type, data, successMessage, buttonSelector, showReload = true, postSuccessCallback = null) {
        $.ajax({
            url: url,
            type: type,
            contentType: "application/json",
            data: data ? JSON.stringify(data) : null,
            beforeSend: function() {
                if (buttonSelector) {
                    $(buttonSelector).prop('disabled', true);
                     $(buttonSelector + ' .spinner-border').show();
                }
            },
            success: function (response) {
                const message = typeof response.detail === 'string' ? response.detail : successMessage;
                Swal.fire("Success!", message, "success").then(() => {
                    if (showReload && !postSuccessCallback) {
                        location.reload();
                    } else if (postSuccessCallback) {
                        postSuccessCallback(response);
                    }
                });
            },
            error: function (xhr, status, error) {
                let errorMessage = "An unexpected error occurred.";
                if (xhr.responseJSON && xhr.responseJSON.detail) {
                    const detail = xhr.responseJSON.detail;
                    if (Array.isArray(detail)) {
                        errorMessage = detail.map(err => `Error in '${err.loc[1]}': ${err.msg}`).join('\n');
                    } else if (typeof detail === 'string') {
                        let userMessage = detail;
                        const failMarker = 'failed with exit code';
                        const markerIndex = detail.indexOf(failMarker);
                        if (markerIndex > -1) {
                            const colonIndex = detail.indexOf(':', markerIndex);
                            if (colonIndex > -1) {
                                userMessage = detail.substring(colonIndex + 1).trim();
                            }
                        }
                        errorMessage = userMessage;
                    }
                }
                Swal.fire("Error!", errorMessage, "error");
            },
            complete: function() {
                if (buttonSelector) {
                    $(buttonSelector).prop('disabled', false);
                    $(buttonSelector + ' .spinner-border').hide();
                }
            }
        });
    }

    function validateForm(formId) {
        let isValid = true;
        $(`#${formId} .form-control:visible`).each(function () {
            const input = $(this);
            const id = input.attr('id');
            let fieldValid = true;

            if (id === 'sni_domain') {
                fieldValid = isValidDomain(input.val());
            } else if (id === 'hysteria_port') {
                fieldValid = isValidPort(input.val());
            }

            if (!fieldValid) {
                input.addClass('is-invalid');
                isValid = false;
            } else {
                input.removeClass('is-invalid');
            }
        });
        return isValid;
    }

    function initUI() {
        $.get(API_URLS.getPort, data => $("#hysteria_port").val(data.port || ""));
        $.get(API_URLS.getSni, data => $("#sni_domain").val(data.sni || ""));
    }

    function fetchAllStatuses() {
        Promise.all([
            $.ajax({ url: API_URLS.checkObfs, type: "GET" }),
            $.ajax({ url: API_URLS.checkMasquerade, type: "GET" })
        ]).then(([obfsResponse, masqueradeResponse]) => {
            const obfsStatus = obfsResponse.obfs;
            const masqueradeStatus = masqueradeResponse.status;
            
            const isObfsActive = obfsStatus === "OBFS is active.";
            const isMasqueradeActive = masqueradeStatus === "Enabled";

            updateObfsUI(obfsStatus, isMasqueradeActive);
            updateMasqueradeUI(masqueradeStatus, isObfsActive);

        }).catch(error => {
            console.error("Failed to fetch statuses:", error);
            $("#obfs_status_message").html('<span class="text-danger">Failed to fetch status.</span>');
            $("#masquerade_status_message").html('<span class="text-danger">Failed to fetch status.</span>');
        });
    }
    
    function updateObfsUI(statusMessage, isMasqueradeEnabled) {
        const container = $("#obfs_status_container");
        const msgElement = $("#obfs_status_message");
        const enableBtn = $("#obfs_enable_btn");
        const disableBtn = $("#obfs_disable_btn");

        container.removeClass("border-success alert-success border-warning alert-warning border-danger alert-danger border-info alert-info");
        enableBtn.hide();
        disableBtn.hide();

        if (isMasqueradeEnabled) {
            msgElement.text("Cannot be managed while Masquerade is active.");
            container.addClass("border-info alert-info");
        } else if (statusMessage === "OBFS is active.") {
            msgElement.text(statusMessage);
            disableBtn.show();
            container.addClass("border-success alert-success");
        } else if (statusMessage === "OBFS is not active.") {
            msgElement.text(statusMessage);
            enableBtn.show();
            container.addClass("border-warning alert-warning");
        } else {
            msgElement.html(`<span class="text-danger">${statusMessage}</span>`);
            container.addClass("border-danger alert-danger");
        }
    }

    function updateMasqueradeUI(statusMessage, isObfsEnabled) {
        const container = $("#masquerade_status_container");
        const msgElement = $("#masquerade_status_message");
        const enableBtn = $("#masquerade_enable_btn");
        const disableBtn = $("#masquerade_disable_btn");
        
        container.removeClass("border-success alert-success border-warning alert-warning border-danger alert-danger border-info alert-info");
        enableBtn.hide();
        disableBtn.hide();

        if (isObfsEnabled) {
            msgElement.text("Cannot be managed while OBFS is active.");
            container.addClass("border-info alert-info");
        } else if (statusMessage === "Enabled") {
            msgElement.text(statusMessage);
            disableBtn.show();
            container.addClass("border-success alert-success");
        } else if (statusMessage === "Disabled") {
            msgElement.text(statusMessage);
            enableBtn.show();
            container.addClass("border-warning alert-warning");
        } else {
            msgElement.html(`<span class="text-danger">${statusMessage}</span>`);
            container.addClass("border-danger alert-danger");
        }
    }

    function enableObfs() {
        confirmAction(
            "Enable OBFS?", 
            "This will require all users to update their configuration files to reconnect.", 
            () => sendRequest(API_URLS.enableObfs, "GET", null, "OBFS enabled successfully!", "#obfs_enable_btn", false, fetchAllStatuses)
        );
    }

    function disableObfs() {
        confirmAction(
            "Disable OBFS?", 
            "This will disconnect all current users. They must update their configurations to reconnect.", 
            () => sendRequest(API_URLS.disableObfs, "GET", null, "OBFS disabled successfully!", "#obfs_disable_btn", false, fetchAllStatuses)
        );
    }

    function enableMasquerade() {
        confirmAction(
            "Enable Masquerade?", 
            "This will enable the string masquerade mode.", 
            () => sendRequest(API_URLS.enableMasquerade, "GET", null, "Masquerade enabled successfully!", "#masquerade_enable_btn", false, fetchAllStatuses)
        );
    }

    function disableMasquerade() {
        confirmAction(
            "Disable Masquerade?", 
            "This will disable the masquerade feature.", 
            () => sendRequest(API_URLS.disableMasquerade, "GET", null, "Masquerade disabled successfully!", "#masquerade_disable_btn", false, fetchAllStatuses)
        );
    }

    function changePort() {
        if (!validateForm('port_form')) return;
        const port = $("#hysteria_port").val();
        const url = API_URLS.setPortTemplate.replace("PORT_PLACEHOLDER", port);
        confirmAction("Are you sure?", "Do you really want to change the port?", () => {
            sendRequest(url, "GET", null, "Port changed successfully!", "#port_change");
        });
    }

    function changeSNI() {
        if (!validateForm('sni_form')) return;
        const domain = $("#sni_domain").val();
        const url = API_URLS.setSniTemplate.replace("SNI_PLACEHOLDER", domain);
        confirmAction("Are you sure?", "Do you really want to change the SNI?", () => {
            sendRequest(url, "GET", null, "SNI changed successfully!", "#sni_change");
        });
    }

    function updateGeo(country) {
        const countryName = country.charAt(0).toUpperCase() + country.slice(1);
        const buttonId = `#geo_update_${country}`;
        const url = API_URLS.updateGeoTemplate.replace('COUNTRY_PLACEHOLDER', country);

        confirmAction(
            "Update Geo Files?", 
            `Do you really want to update the Geo files for ${countryName}?`, 
            () => sendRequest(url, "GET", null, `Geo files for ${countryName} updated successfully!`, buttonId, false, null)
        );
    }

    initUI();
    fetchAllStatuses();

    $("#port_change").on("click", changePort);
    $("#sni_change").on("click", changeSNI);
    $("#obfs_enable_btn").on("click", enableObfs);
    $("#obfs_disable_btn").on("click", disableObfs);
    $("#masquerade_enable_btn").on("click", enableMasquerade);
    $("#masquerade_disable_btn").on("click", disableMasquerade);
    $("#geo_update_iran").on("click", () => updateGeo('iran'));
    $("#geo_update_china").on("click", () => updateGeo('china'));
    $("#geo_update_russia").on("click", () => updateGeo('russia'));

    $('#sni_domain, #hysteria_port').on('input', function () {
        const validator = $(this).attr('id') === 'sni_domain' ? isValidDomain : isValidPort;
        if (validator($(this).val())) {
            $(this).removeClass('is-invalid');
        } else if ($(this).val().trim() !== "") {
            $(this).addClass('is-invalid');
        } else {
             $(this).removeClass('is-invalid');
        }
    });
});