const locateButtons = document.querySelectorAll('[data-locate]');
const resetMapButtons = document.querySelectorAll('[data-map-reset]');
const mapContainers = document.querySelectorAll('[data-map-picker]');
const mapPickers = [];
const DEFAULT_LATITUDE = 27.7172;
const DEFAULT_LONGITUDE = 85.3240;
const DEFAULT_ZOOM = 12;

const getLatInput = () => document.querySelector('#id_latitude');
const getLonInput = () => document.querySelector('#id_longitude');

const writeCoordinates = (latitude, longitude) => {
    const latInput = getLatInput();
    const lonInput = getLonInput();
    if (!latInput || !lonInput) {
        return;
    }
    latInput.value = latitude.toFixed(6);
    lonInput.value = longitude.toFixed(6);
};

const syncFromInputsToMap = (picker) => {
    const latInput = getLatInput();
    const lonInput = getLonInput();
    if (!latInput || !lonInput) {
        return;
    }

    const latitude = Number.parseFloat(latInput.value);
    const longitude = Number.parseFloat(lonInput.value);
    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
        return;
    }
    picker.setMarker(latitude, longitude, false);
};

if (typeof window.L !== 'undefined') {
    mapContainers.forEach((container) => {
        container.innerHTML = '';
        const latInput = getLatInput();
        const lonInput = getLonInput();
        const initialLatitude = latInput ? Number.parseFloat(latInput.value) : Number.NaN;
        const initialLongitude = lonInput ? Number.parseFloat(lonInput.value) : Number.NaN;

        const hasInitialCoordinates = !Number.isNaN(initialLatitude) && !Number.isNaN(initialLongitude);

        const map = L.map(container).setView(
            hasInitialCoordinates ? [initialLatitude, initialLongitude] : [DEFAULT_LATITUDE, DEFAULT_LONGITUDE],
            hasInitialCoordinates ? 14 : DEFAULT_ZOOM
        );

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map);

        let marker = null;
        const setMarker = (latitude, longitude, updateInputs = true) => {
            if (marker) {
                marker.setLatLng([latitude, longitude]);
            } else {
                marker = L.marker([latitude, longitude], { draggable: true }).addTo(map);
                marker.on('dragend', () => {
                    const point = marker.getLatLng();
                    writeCoordinates(point.lat, point.lng);
                });
            }
            map.panTo([latitude, longitude]);
            if (updateInputs) {
                writeCoordinates(latitude, longitude);
            }
        };

        if (hasInitialCoordinates) {
            setMarker(initialLatitude, initialLongitude, false);
        }

        map.on('click', (event) => {
            setMarker(event.latlng.lat, event.latlng.lng, true);
        });

        const resetView = () => {
            map.setView([DEFAULT_LATITUDE, DEFAULT_LONGITUDE], DEFAULT_ZOOM);
        };

        mapPickers.push({ setMarker, resetView });
    });
} else {
    mapContainers.forEach((container) => {
        container.innerHTML = '<p class="map-fallback">Map failed to load. You can still use "Use my location" or enter coordinates manually.</p>';
    });
}

locateButtons.forEach((button) => {
    button.addEventListener('click', () => {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by this browser.');
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (position) => {
                writeCoordinates(position.coords.latitude, position.coords.longitude);
                mapPickers.forEach((picker) => {
                    picker.setMarker(position.coords.latitude, position.coords.longitude, false);
                });
            },
            () => {
                alert('Unable to fetch your location. Please enter it manually.');
            },
            { enableHighAccuracy: true, timeout: 5000 }
        );
    });
});

resetMapButtons.forEach((button) => {
    button.addEventListener('click', () => {
        mapPickers.forEach((picker) => {
            picker.resetView();
        });
    });
});

const latitudeInput = getLatInput();
const longitudeInput = getLonInput();
if (latitudeInput && longitudeInput && mapPickers.length > 0) {
    latitudeInput.addEventListener('change', () => {
        mapPickers.forEach((picker) => syncFromInputsToMap(picker));
    });
    longitudeInput.addEventListener('change', () => {
        mapPickers.forEach((picker) => syncFromInputsToMap(picker));
    });
}
