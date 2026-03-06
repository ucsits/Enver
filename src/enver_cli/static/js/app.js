const pdfjsLib = window.pdfjsLib;
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

const elements = {
    signature: { x: 50, y: 50, scale: 1.0, image: null, visible: true },
    stamp: { x: 300, y: 50, scale: 1.0, image: null, visible: true },
    qr: { x: 66, y: 62.5, width: 64, height: 64, visible: true }
};

let selectedElement = null;
let isDragging = false;
let isResizing = false;
let dragOffset = { x: 0, y: 0 };
let resizeHandle = null;
let currentZoom = 1.0;
let gridSnap = false;
let pdfDoc = null;
let currentPage = 1;
let pageCount = 0;
let canvasScale = 1.0;
let renderScale = 1.5;
let pdfPageWidth = 0;
let pdfPageHeight = 0;

const canvas = document.getElementById('pdf-canvas');
const ctx = canvas.getContext('2d');
const elementsLayer = document.getElementById('elements-layer');
const canvasContainer = document.getElementById('canvas-container');

function init() {
    setupFileUploads();
    setupElementSelection();
    setupControls();
    setupZoom();
    setupSigning();
}

function setupFileUploads() {
    const pdfInput = document.getElementById('pdf-input');
    const sigInput = document.getElementById('signature-input');
    const stampInput = document.getElementById('stamp-input');

    pdfInput.addEventListener('change', (e) => loadPDF(e.target.files[0]));
    sigInput.addEventListener('change', (e) => loadImage(e.target.files[0], 'signature'));
    stampInput.addEventListener('change', (e) => loadImage(e.target.files[0], 'stamp'));

    setupDropZone('pdf-drop-zone', pdfInput);
    setupDropZone('sig-drop-zone', sigInput);
    setupDropZone('stamp-drop-zone', stampInput);
}

function setupDropZone(zoneId, input) {
    const zone = document.getElementById(zoneId);
    
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.style.borderColor = '#3498db';
    });

    zone.addEventListener('dragleave', () => {
        zone.style.borderColor = '#ddd';
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.style.borderColor = '#ddd';
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            input.files = files;
            input.dispatchEvent(new Event('change'));
        }
    });
}

async function loadPDF(file) {
    if (!file || file.type !== 'application/pdf') {
        showError('Please select a valid PDF file');
        return;
    }

    try {
        const arrayBuffer = await file.arrayBuffer();
        pdfDoc = await pdfjsLib.getDocument(arrayBuffer).promise;
        pageCount = pdfDoc.numPages;
        currentPage = 1;
        
        document.getElementById('page-number').max = pageCount;
        document.getElementById('page-count').textContent = `of ${pageCount}`;
        
        await renderPage(1);
        hideError();
    } catch (err) {
        showError('Failed to load PDF: ' + err.message);
    }
}

async function renderPage(pageNum) {
    if (!pdfDoc) return;

    try {
        const page = await pdfDoc.getPage(pageNum);
        const viewport = page.getViewport({ scale: renderScale });
        
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = viewport.width + 'px';
        canvas.style.height = viewport.height + 'px';
        
        pdfPageWidth = page.view[2];
        pdfPageHeight = page.view[3];
        canvasScale = viewport.width / pdfPageWidth;
        
        await page.render({
            canvasContext: ctx,
            viewport: viewport
        }).promise;

        elementsLayer.style.width = viewport.width + 'px';
        elementsLayer.style.height = viewport.height + 'px';
        
        updateElementPositions();
    } catch (err) {
        showError('Failed to render page: ' + err.message);
    }
}

function loadImage(file, type) {
    if (!file || !file.type.startsWith('image/')) {
        showError('Please select a valid image file');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        elements[type].image = e.target.result;
        const el = document.getElementById(`${type}-el`);
        el.style.backgroundImage = `url(${e.target.result})`;
        
        const img = new Image();
        img.onload = () => {
            const w = img.width * elements[type].scale;
            const h = img.height * elements[type].scale;
            el.style.width = w + 'px';
            el.style.height = h + 'px';
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function setupElementSelection() {
    const elementTypes = ['signature', 'stamp', 'qr'];
    
    elementTypes.forEach(type => {
        const el = document.getElementById(`${type}-el`);
        
        el.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('resize-handle')) {
                startResize(e, type);
            } else {
                startDrag(e, type);
            }
        });
    });

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
}

function startDrag(e, type) {
    e.preventDefault();
    e.stopPropagation();
    
    selectElement(type);
    isDragging = true;
    
    const el = document.getElementById(`${type}-el`);
    const rect = el.getBoundingClientRect();
    const containerRect = canvasContainer.getBoundingClientRect();
    const scrollX = canvasContainer.scrollLeft || 0;
    const scrollY = canvasContainer.scrollTop || 0;
    
    const canvasX = e.clientX - containerRect.left + scrollX;
    const canvasY = e.clientY - containerRect.top + scrollY;
    
    dragOffset.x = (canvasX / currentZoom) - elements[type].x * renderScale;
    dragOffset.y = (canvasY / currentZoom) - elements[type].y * renderScale;
}

function startResize(e, type) {
    e.preventDefault();
    e.stopPropagation();
    
    selectElement(type);
    isResizing = true;
    resizeHandle = e.target.classList[1];
}

function handleMouseMove(e) {
    if (!selectedElement) return;

    if (isDragging) {
        const containerRect = canvasContainer.getBoundingClientRect();
        const scrollX = canvasContainer.scrollLeft || 0;
        const scrollY = canvasContainer.scrollTop || 0;
        const canvasX = e.clientX - containerRect.left + scrollX;
        const canvasY = e.clientY - containerRect.top + scrollY;
        const displayX = canvasX / currentZoom;
        const displayY = canvasY / currentZoom;
        let x = displayX - dragOffset.x;
        let y = displayY - dragOffset.y;
        
        if (gridSnap) {
            x = Math.round(x / 10) * 10;
            y = Math.round(y / 10) * 10;
        }
        
        x = Math.max(0, Math.min(x, pdfPageWidth));
        y = Math.max(0, Math.min(y, pdfPageHeight));
        
        elements[selectedElement].x = x;
        elements[selectedElement].y = y;
        
        updateElementPositions();
        updateControlValues();
    } else if (isResizing && selectedElement !== 'qr') {
        const el = document.getElementById(`${selectedElement}-el`);
        const rect = el.getBoundingClientRect();
        const containerRect = canvasContainer.getBoundingClientRect();
        const scrollX = canvasContainer.scrollLeft || 0;
        const scrollY = canvasContainer.scrollTop || 0;
        
        let newWidth, newHeight;
        
        if (resizeHandle.includes('e')) {
            newWidth = (e.clientX - containerRect.left + scrollX - rect.left) / currentZoom;
        }
        if (resizeHandle.includes('w')) {
            newWidth = (rect.right - (e.clientX - containerRect.left + scrollX)) / currentZoom;
            elements[selectedElement].x += (rect.width - newWidth) / (renderScale * currentZoom);
        }
        if (resizeHandle.includes('s')) {
            newHeight = (e.clientY - containerRect.top + scrollY - rect.top) / currentZoom;
        }
        if (resizeHandle.includes('n')) {
            newHeight = (rect.bottom - (e.clientY - containerRect.top + scrollY)) / currentZoom;
            elements[selectedElement].y += (rect.height - newHeight) / (renderScale * currentZoom);
        }
        
        if (newWidth && newHeight) {
            const originalImage = elements[selectedElement].image;
            if (originalImage) {
                const img = new Image();
                img.onload = () => {
                    const scale = newWidth / img.width;
                    elements[selectedElement].scale = scale;
                    const scaleInput = document.getElementById(`${selectedElement}-scale`);
                    const scaleVal = document.getElementById(`${selectedElement}-scale-val`);
                    if (scaleInput) scaleInput.value = scale;
                    if (scaleVal) scaleVal.textContent = scale.toFixed(1);
                    updateElementPositions();
                    updateControlValues();
                };
                img.src = originalImage;
            }
        }
    }
}

function handleMouseUp() {
    isDragging = false;
    isResizing = false;
    resizeHandle = null;
}

function selectElement(type) {
    document.querySelectorAll('.element').forEach(el => el.classList.remove('selected'));
    document.getElementById(`${type}-el`).classList.add('selected');
    selectedElement = type;
}

function updateElementPositions() {
    ['signature', 'stamp', 'qr'].forEach(type => {
        const el = document.getElementById(`${type}-el`);
        const data = elements[type];
        
        if (!data.visible) {
            el.style.display = 'none';
            return;
        }
        
        el.style.display = 'block';
        
        const canvasX = data.x * renderScale * currentZoom;
        const canvasY = data.y * renderScale * currentZoom;
        
        if (type === 'qr') {
            el.style.left = canvasX + 'px';
            el.style.top = canvasY + 'px';
            el.style.width = (data.width * renderScale * currentZoom) + 'px';
            el.style.height = (data.height * renderScale * currentZoom) + 'px';
        } else {
            el.style.left = canvasX + 'px';
            el.style.top = canvasY + 'px';
            
            if (data.image) {
                const img = new Image();
                img.onload = () => {
                    const w = img.width * data.scale * renderScale * currentZoom;
                    const h = img.height * data.scale * renderScale * currentZoom;
                    el.style.width = w + 'px';
                    el.style.height = h + 'px';
                };
                img.src = data.image;
            }
        }
    });
}

function setupControls() {
    document.getElementById('sig-x').addEventListener('input', (e) => {
        if (selectedElement === 'signature') {
            elements.signature.x = parseFloat(e.target.value) || 0;
            updateElementPositions();
        }
    });

    document.getElementById('sig-y').addEventListener('input', (e) => {
        if (selectedElement === 'signature') {
            elements.signature.y = parseFloat(e.target.value) || 0;
            updateElementPositions();
        }
    });

    document.getElementById('signature-scale').addEventListener('input', (e) => {
        elements.signature.scale = parseFloat(e.target.value);
        document.getElementById('signature-scale-val').textContent = parseFloat(e.target.value).toFixed(1);
        updateElementPositions();
    });

    document.getElementById('stamp-x').addEventListener('input', (e) => {
        if (selectedElement === 'stamp') {
            elements.stamp.x = parseFloat(e.target.value) || 0;
            updateElementPositions();
        }
    });

    document.getElementById('stamp-y').addEventListener('input', (e) => {
        if (selectedElement === 'stamp') {
            elements.stamp.y = parseFloat(e.target.value) || 0;
            updateElementPositions();
        }
    });

    document.getElementById('stamp-scale').addEventListener('input', (e) => {
        elements.stamp.scale = parseFloat(e.target.value);
        document.getElementById('stamp-scale-val').textContent = parseFloat(e.target.value).toFixed(1);
        updateElementPositions();
    });

    document.getElementById('qr-x').addEventListener('input', (e) => {
        elements.qr.x = parseFloat(e.target.value) || 0;
        updateElementPositions();
    });

    document.getElementById('qr-y').addEventListener('input', (e) => {
        elements.qr.y = parseFloat(e.target.value) || 0;
        updateElementPositions();
    });

    document.getElementById('show-stamp').addEventListener('change', (e) => {
        elements.stamp.visible = e.target.checked;
        updateElementPositions();
    });

    document.getElementById('show-qr').addEventListener('change', (e) => {
        elements.qr.visible = e.target.checked;
        updateElementPositions();
    });

    document.getElementById('load-page').addEventListener('click', () => {
        const pageNum = parseInt(document.getElementById('page-number').value);
        if (pageNum >= 1 && pageNum <= pageCount) {
            currentPage = pageNum;
            renderPage(pageNum);
        }
    });
}

function updateControlValues() {
    if (selectedElement === 'signature') {
        document.getElementById('sig-x').value = Math.round(elements.signature.x);
        document.getElementById('sig-y').value = Math.round(elements.signature.y);
    } else if (selectedElement === 'stamp') {
        document.getElementById('stamp-x').value = Math.round(elements.stamp.x);
        document.getElementById('stamp-y').value = Math.round(elements.stamp.y);
    } else if (selectedElement === 'qr') {
        document.getElementById('qr-x').value = Math.round(elements.qr.x);
        document.getElementById('qr-y').value = Math.round(elements.qr.y);
    }
}

function setupZoom() {
    document.getElementById('zoom-in').addEventListener('click', () => {
        currentZoom = Math.min(2.0, currentZoom + 0.1);
        document.getElementById('zoom-level').textContent = Math.round(currentZoom * 100) + '%';
        updateElementPositions();
    });

    document.getElementById('zoom-out').addEventListener('click', () => {
        currentZoom = Math.max(0.5, currentZoom - 0.1);
        document.getElementById('zoom-level').textContent = Math.round(currentZoom * 100) + '%';
        updateElementPositions();
    });

    document.getElementById('grid-snap').addEventListener('click', (e) => {
        gridSnap = !gridSnap;
        e.target.textContent = `Grid Snap: ${gridSnap ? 'On' : 'Off'}`;
    });
}

function setupSigning() {
    document.getElementById('sign-btn').addEventListener('click', async () => {
        const pdfInput = document.getElementById('pdf-input');
        const sigInput = document.getElementById('signature-input');
        const stampInput = document.getElementById('stamp-input');
        const privateKey = document.getElementById('private-key').value;
        
        if (!pdfInput.files[0] || !sigInput.files[0]) {
            showError('Please upload a PDF and signature image');
            return;
        }

        if (!privateKey) {
            showError('Please enter your private key');
            return;
        }

        const formData = new FormData();
        formData.append('pdf', pdfInput.files[0]);
        formData.append('signature', sigInput.files[0]);
        
        if (stampInput.files[0]) {
            formData.append('stamp', stampInput.files[0]);
        }
        
        formData.append('private_key', privateKey);
        formData.append('organization', document.getElementById('organization').value);
        formData.append('rpc_url', document.getElementById('rpc-url').value);
        formData.append('page_number', currentPage);
        
        formData.append('sig_x', elements.signature.x);
        formData.append('sig_y', elements.signature.y);
        formData.append('sig_scale', elements.signature.scale);
        
        formData.append('qr_x', elements.qr.x);
        formData.append('qr_y', elements.qr.y);
        
        formData.append('stamp_x', elements.stamp.x);
        formData.append('stamp_y', elements.stamp.y);
        formData.append('stamp_scale', elements.stamp.scale);

        const progress = document.getElementById('progress');
        const result = document.getElementById('result');
        const error = document.getElementById('error');
        const signBtn = document.getElementById('sign-btn');

        progress.classList.remove('hidden');
        result.classList.add('hidden');
        error.classList.add('hidden');
        signBtn.disabled = true;

        try {
            const response = await fetch('/sign', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                document.getElementById('download-link').href = data.download_url;
                result.classList.remove('hidden');
            } else {
                throw new Error(data.error || 'Signing failed');
            }
        } catch (err) {
            showError(err.message);
        } finally {
            progress.classList.add('hidden');
            signBtn.disabled = false;
        }
    });
}

function showError(message) {
    const error = document.getElementById('error');
    error.querySelector('.error-msg').textContent = message;
    error.classList.remove('hidden');
}

function hideError() {
    document.getElementById('error').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', init);
