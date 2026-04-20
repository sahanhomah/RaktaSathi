(function () {
    const input = document.querySelector('#id_prescription_image');
    if (!input) {
        return;
    }

    const form = input.closest('form');
    const messageNode = document.querySelector('#prescriptionValidationMessage');

    const toNumber = (value, fallback) => {
        const parsed = Number.parseFloat(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    };

    const maxBytes = toNumber(input.dataset.maxBytes, 5 * 1024 * 1024);
    const minWidth = toNumber(input.dataset.minWidth, 300);
    const minHeight = toNumber(input.dataset.minHeight, 300);
    const minBrightRatio = toNumber(input.dataset.minBrightRatio, 0.5);
    const minTextRatio = toNumber(input.dataset.minTextRatio, 0.005);
    const maxTextRatio = toNumber(input.dataset.maxTextRatio, 0.45);
    const textPixelThreshold = toNumber(input.dataset.textPixelThreshold, 140);
    const minEdgeRatio = toNumber(input.dataset.minEdgeRatio, 0.003);

    const allowedMimeTypes = new Set(['image/jpeg', 'image/png']);
    const allowedExtensions = new Set(['jpg', 'jpeg', 'png']);

    const setFeedback = (text, isError) => {
        if (!messageNode) {
            return;
        }
        messageNode.textContent = text || '';
        messageNode.classList.remove('text-danger', 'text-success', 'text-muted');
        if (!text) {
            return;
        }
        messageNode.classList.add(isError ? 'text-danger' : 'text-success');
    };

    const extensionFromName = (name) => {
        const parts = String(name || '').toLowerCase().split('.');
        if (parts.length < 2) {
            return '';
        }
        return parts[parts.length - 1];
    };

    const getImageMetrics = (image) => {
        const width = 200;
        const height = 200;
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext('2d', { willReadFrequently: true });
        context.drawImage(image, 0, 0, width, height);

        const imageData = context.getImageData(0, 0, width, height).data;
        const totalPixels = width * height;
        let brightPixels = 0;
        let textPixels = 0;

        const gray = new Uint8ClampedArray(totalPixels);
        for (let i = 0; i < totalPixels; i += 1) {
            const base = i * 4;
            const r = imageData[base];
            const g = imageData[base + 1];
            const b = imageData[base + 2];
            const luminance = Math.round((r * 0.299) + (g * 0.587) + (b * 0.114));
            gray[i] = luminance;
            if (luminance >= 200) {
                brightPixels += 1;
            }
            if (luminance <= textPixelThreshold) {
                textPixels += 1;
            }
        }

        let edgePixels = 0;
        for (let y = 1; y < height - 1; y += 1) {
            for (let x = 1; x < width - 1; x += 1) {
                const index = (y * width) + x;
                const gx =
                    -gray[index - width - 1] + gray[index - width + 1]
                    - (2 * gray[index - 1]) + (2 * gray[index + 1])
                    - gray[index + width - 1] + gray[index + width + 1];
                const gy =
                    gray[index - width - 1] + (2 * gray[index - width]) + gray[index - width + 1]
                    - gray[index + width - 1] - (2 * gray[index + width]) - gray[index + width + 1];
                const magnitude = Math.abs(gx) + Math.abs(gy);
                if (magnitude >= 120) {
                    edgePixels += 1;
                }
            }
        }

        return {
            brightRatio: brightPixels / totalPixels,
            textRatio: textPixels / totalPixels,
            edgeRatio: edgePixels / totalPixels,
        };
    };

    const validateFile = (file) => new Promise((resolve) => {
        if (!file) {
            resolve({ ok: false, message: 'Please upload the prescription image.' });
            return;
        }

        const ext = extensionFromName(file.name);
        if (!allowedExtensions.has(ext)) {
            resolve({ ok: false, message: 'Only JPG and PNG files are allowed.' });
            return;
        }

        if (file.type && !allowedMimeTypes.has(file.type.toLowerCase())) {
            resolve({ ok: false, message: 'Only JPG and PNG files are allowed.' });
            return;
        }

        if (file.size > maxBytes) {
            const maxMb = maxBytes / (1024 * 1024);
            resolve({ ok: false, message: `Prescription image size must be ${maxMb.toFixed(2)} MB or less.` });
            return;
        }

        const objectUrl = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => {
            try {
                if (img.naturalWidth < minWidth || img.naturalHeight < minHeight) {
                    resolve({
                        ok: false,
                        message: `Prescription image must be at least ${minWidth}x${minHeight} pixels.`,
                    });
                    return;
                }

                const metrics = getImageMetrics(img);
                if (metrics.brightRatio < minBrightRatio) {
                    resolve({ ok: false, message: 'Prescription image must clearly show a paper-like document background.' });
                    return;
                }
                if (metrics.textRatio < minTextRatio || metrics.textRatio > maxTextRatio) {
                    resolve({ ok: false, message: 'Prescription image must contain visible text on the document.' });
                    return;
                }
                if (metrics.edgeRatio < minEdgeRatio) {
                    resolve({ ok: false, message: 'Prescription image appears unclear. Please upload a clearer document photo.' });
                    return;
                }

                resolve({ ok: true, message: 'Prescription image looks valid and ready to submit.' });
            } finally {
                URL.revokeObjectURL(objectUrl);
            }
        };
        img.onerror = () => {
            URL.revokeObjectURL(objectUrl);
            resolve({ ok: false, message: 'Upload a valid prescription image file.' });
        };
        img.src = objectUrl;
    });

    const applyValidationResult = (result) => {
        if (result.ok) {
            input.setCustomValidity('');
            setFeedback(result.message, false);
            return true;
        }
        input.setCustomValidity(result.message);
        setFeedback(result.message, true);
        return false;
    };

    const runValidation = async () => {
        if (!input.files || input.files.length === 0) {
            input.setCustomValidity('Please upload the prescription image.');
            setFeedback('Please upload the prescription image.', true);
            return false;
        }
        setFeedback('Validating prescription image...', false);
        const result = await validateFile(input.files[0]);
        return applyValidationResult(result);
    };

    input.addEventListener('change', () => {
        runValidation();
    });

    if (form) {
        form.addEventListener('submit', async (event) => {
            const isValid = await runValidation();
            if (!isValid) {
                event.preventDefault();
                input.reportValidity();
            }
        });
    }
})();
