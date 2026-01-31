const map = L.map('map').setView([18.5204, 73.8567], 11); // Pune Center

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
}).addTo(map);

// Truck Icons
const truckIcon = L.icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/741/741407.png', // Placeholder
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16]
});

const markers = {}; // Store markers by truck_id

async function fetchState() {
    try {
        const response = await fetch('/api/state');
        const data = await response.json();

        // Update Clock
        document.getElementById('clock').innerText = data.time;

        // Update Trucks
        const listContainer = document.getElementById('truck-list');
        listContainer.innerHTML = ''; // Clear list

        data.trucks.forEach(truck => {
            // Update Map Marker
            if (markers[truck.truck_id]) {
                const marker = markers[truck.truck_id];
                marker.setLatLng([truck.location.lat, truck.location.lng]);
                marker.setPopupContent(`<b>${truck.truck_id}</b><br>Status: ${truck.status}<br>Fuel: ${truck.fuel_percent}%`);
            } else {
                const marker = L.marker([truck.location.lat, truck.location.lng], { icon: truckIcon })
                    .addTo(map)
                    .bindPopup(`<b>${truck.truck_id}</b>`);
                markers[truck.truck_id] = marker;
            }

            // Update List Item
            const item = document.createElement('div');
            item.className = 'p-3 bg-white rounded-lg shadow-sm border-l-4 ' +
                (truck.status === 'EN_ROUTE' ? 'border-green-500' : 'border-yellow-500');
            item.innerHTML = `
                <div class="flex justify-between items-center">
                    <span class="font-bold text-gray-800">${truck.truck_id}</span>
                    <span class="text-xs bg-gray-100 px-2 py-1 rounded">${truck.status}</span>
                </div>
                <div class="text-xs text-gray-500 mt-1">
                    Fuel: ${truck.fuel_percent}% | Route: ${truck.current_node} -> ${truck.route_nodes[0] || 'End'}
                </div>
            `;
            listContainer.appendChild(item);
        });

    } catch (e) {
        console.error("Error fetching state:", e);
    }
}

// Poll every 1 second
setInterval(fetchState, 1000);
