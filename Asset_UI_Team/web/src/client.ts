/// <reference types="google.maps" />

interface GeoCenter {
    lat: number;
    lon: number;
    impact_radius_km: number;
}

interface RiskSignal {
    risk_score: number;
    location: string;
    primary_driver: string;
    estimated_impact: string;
    geo_center: GeoCenter;
}

// Function to render the list of risks in the sidebar
function renderRiskList(risks: RiskSignal[]) {
    const riskListElement = document.getElementById('risk-list');
    if (!riskListElement) return;

    riskListElement.innerHTML = ''; // Clear loading text

    risks.forEach((risk) => {
        const card = document.createElement('div');
        card.className = 'risk-card';
        card.innerHTML = `
            <h3>${risk.location}</h3>
            <div class="risk-detail">
                <strong>Score:</strong> ${risk.risk_score}
            </div>
            <div class="risk-detail">
                <strong>Driver:</strong> ${risk.primary_driver}
            </div>
            <div class="risk-detail">
                <strong>Impact:</strong> ${risk.estimated_impact}
            </div>
        `;
        riskListElement.appendChild(card);
    });
}

// Function to initialize the Google Map and markers
async function initMap(risks: RiskSignal[]) {
    try {
        const { Map } = await google.maps.importLibrary("maps") as google.maps.MapsLibrary;
        const { AdvancedMarkerElement } = await google.maps.importLibrary("marker") as google.maps.MarkerLibrary;

        const map = new Map(document.getElementById("map") as HTMLElement, {
            center: { lat: 39.8283, lng: -98.5795 }, // Center of USA
            zoom: 4,
            mapId: "DEMO_MAP_ID", 
        });

        risks.forEach((risk) => {
            const position = { 
                lat: risk.geo_center.lat, 
                lng: risk.geo_center.lon 
            };

            const marker = new AdvancedMarkerElement({
                map,
                position,
                title: risk.location,
            });

            const contentString = `
                <div class="info-window">
                    <h4>${risk.location}</h4>
                    <p><strong>Impact:</strong> ${risk.estimated_impact}</p>
                </div>
            `;

            const infoWindow = new google.maps.InfoWindow({
                content: contentString,
            });

            marker.addListener("click", () => {
                infoWindow.open({
                    anchor: marker,
                    map,
                });
            });
        });
    } catch (e) {
        console.error("Google Maps failed to initialize. Please check your API Key.", e);
    }
}

// Main entry point
async function init() {
    try {
        const response = await fetch('/api/risks');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const risks: RiskSignal[] = await response.json();

        // 1. Render List (Independent of Map)
        renderRiskList(risks);

        // 2. Render Map
        await initMap(risks);

    } catch (error) {
        console.error("Failed to load application data:", error);
        const list = document.getElementById('risk-list');
        if (list) list.innerHTML = '<p style="color: #d32f2f;">Failed to load risk data. Check console for details.</p>';
    }
}

window.addEventListener('DOMContentLoaded', init);