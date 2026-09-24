/// <reference types="google.maps" />

interface GeoCenter { lat: number; lon: number; impact_radius_km: number; }
interface RiskSignal {
    risk_score: number; location: string; primary_driver: string;
    estimated_impact: string; recommendation: string; timestamp: string;
    geo_center: GeoCenter;
}

function getRiskLevel(score: number): 'high' | 'moderate' | 'low' {
    if (score > 0.8) return 'high';
    if (score > 0.3) return 'moderate';
    return 'low';
}
function getRiskColor(level: string): string {
    switch (level) {
        case 'high': return 'rgba(220, 38, 38, 0.35)';
        case 'moderate': return 'rgba(230, 160, 0, 0.3)';
        default: return 'rgba(34, 139, 34, 0.25)';
    }
}
function getStrokeColor(level: string): string {
    switch (level) {
        case 'high': return '#dc2626';
        case 'moderate': return '#ca8a04';
        default: return '#16a34a';
    }
}
function fmt(s: string): string { return s.replace(/_/g, ' '); }

function buildRiskMap(risks: RiskSignal[]): Map<string, RiskSignal> {
    const map = new Map<string, RiskSignal>();
    risks.forEach(r => {
        const name = r.location.replace(/_County$/, '').replace(/_/g, ' ');
        map.set(name, r);
    });
    return map;
}

// Recommendations per risk level (power outage focused)
const recommendations: Record<string, { action: string; narrative: string; primary: string; alt: string }> = {
    high: {
        action: 'reroute',
        primary: 'Grid: <span class="text-red">Critical Outage</span>',
        alt: 'Backup: <span class="text-yellow">Limited</span>',
        narrative: 'Activate backup generators. Reroute operations away from affected zones.'
    },
    moderate: {
        action: 'stage',
        primary: 'Grid: <span class="text-yellow">Degraded</span>',
        alt: 'Backup: <span class="text-green">Available</span>',
        narrative: 'Pre-position crews. Prepare load-shedding if conditions escalate.'
    },
    low: {
        action: 'hold',
        primary: 'Grid: <span class="text-green">Stable</span>',
        alt: 'No backup needed',
        narrative: 'Normal operations. Next assessment in 6 hours.'
    }
};

// Evidence chain templates per risk level
interface EvidenceCard { icon: string; title: string; body: string; source: string; cls?: string; }

function getEvidenceCards(risk: RiskSignal, countyName: string): EvidenceCard[] {
    const level = getRiskLevel(risk.risk_score);
    const driver = fmt(risk.primary_driver);
    const score = risk.risk_score;
    const eventTime = risk.timestamp ? new Date(risk.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A';

    if (level === 'high') {
        return [
            { icon: '⚡', title: 'OUTAGE DETECTION', body: `${countyName}: score ${score}. Driver: ${driver}. Critical threshold exceeded (>0.8).`, source: `(Grid Monitor, ${eventTime})` },
            { icon: '📊', title: 'IMPACT ANALYSIS', body: `${risk.estimated_impact.replace(/_/g, ' ')}. Radius: ${risk.geo_center.impact_radius_km} km. Prolonged outage likely.`, source: `(Impact Model v2.1, ${eventTime})` },
            { icon: '🔌', title: 'GRID STATUS', body: `${driver} on distribution feeders. Transmission stressed; cascading risk.`, source: `(Utility SCADA, ${eventTime})`, cls: 'warn' },
            { icon: '🏭', title: 'SUPPLY CHAIN IMPACT', body: `Cold-chain & manufacturing at risk. Reroute loads; activate site backups.`, source: `(Supply Chain Analyzer, ${eventTime})`, cls: 'warn' },
            { icon: '🧠', title: 'RECOMMENDATION', body: `${risk.recommendation || 'Dispatch crews to clear fallen trees; coordinate mutual aid.'}`, source: `(Decision Engine v2.1, ${eventTime})`, cls: 'decision' },
        ];
    } else if (level === 'moderate') {
        return [
            { icon: '⚠️', title: 'OUTAGE RISK ELEVATED', body: `${countyName}: score ${score}. Driver: ${driver}. Below critical threshold.`, source: `(Grid Monitor, ${eventTime})` },
            { icon: '📊', title: 'IMPACT ANALYSIS', body: `${risk.estimated_impact.replace(/_/g, ' ')}. Radius: ${risk.geo_center.impact_radius_km} km. Partial outage possible <24h.`, source: `(Impact Model v2.1, ${eventTime})` },
            { icon: '📡', title: 'GRID MONITORING', body: `${driver} developing. Vegetation & feeder stress indicators rising.`, source: `(Sensor Network, ${eventTime})` },
            { icon: '🔋', title: 'BACKUP READINESS', body: `Verify backup power at critical sites. Pre-stage tree-trimming crews.`, source: `(Facility Manager, ${eventTime})` },
            { icon: '🧠', title: 'RECOMMENDATION', body: `${risk.recommendation || 'Pre-position tree-trimming crews; increase line patrols.'}`, source: `(Decision Engine v2.1, ${eventTime})` },
        ];
    } else {
        return [
            { icon: '✅', title: 'GRID STABLE', body: `${countyName}: score ${score}. No storm-related drivers. Grid normal.`, source: `(Grid Monitor, ${eventTime})` },
            { icon: '📊', title: 'IMPACT ANALYSIS', body: `${risk.estimated_impact.replace(/_/g, ' ')}. No disruption in ${risk.geo_center.impact_radius_km} km zone.`, source: `(Impact Model v2.1, ${eventTime})` },
            { icon: '🔌', title: 'INFRASTRUCTURE STATUS', body: `Feeders & substations nominal; no alerts.`, source: `(Utility SCADA, ${eventTime})` },
            { icon: '📦', title: 'SUPPLY CHAIN STATUS', body: `Facilities fully powered. No backup needed.`, source: `(Facility Manager, ${eventTime})` },
            { icon: '🧠', title: 'RECOMMENDATION', body: `${risk.recommendation || 'Continue routine monitoring.'}`, source: `(Decision Engine v2.1, ${eventTime})` },
        ];
    }
}

function updateEvidencePanel(risk: RiskSignal, countyName: string) {
    const cards = getEvidenceCards(risk, countyName);
    const container = document.getElementById('evidence-cards');
    if (!container) return;

    container.innerHTML = cards.map(c =>
        `<div class="ev-card ${c.cls || ''}">
            <div class="ev-head"><div class="ev-icon">${c.icon}</div><div class="ev-title">${c.title}</div></div>
            <div class="ev-body">${c.body}</div>
            <div class="ev-source">${c.source}</div>
        </div>`
    ).join('');

    // Update audit trail
    const level = getRiskLevel(risk.risk_score);
    const auditTs = document.getElementById('audit-ts');
    const auditList = document.getElementById('audit-list');
    const eventTimestamp = risk.timestamp ? new Date(risk.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A';
    if (auditTs) auditTs.textContent = eventTimestamp;
    if (auditList) {
        const decisionId = '#' + Math.floor(100000 + Math.random() * 900000);
        auditList.innerHTML = `
            <div class="audit-row"><span class="audit-label">Region:</span> <span>${countyName} County</span></div>
            <div class="audit-row"><span class="audit-label">Event Time:</span> <span>${eventTimestamp}</span></div>
            <div class="audit-row"><span class="audit-label">Risk Level:</span> <span style="color:${getStrokeColor(level)};font-weight:600">${level.toUpperCase()} (${risk.risk_score})</span></div>
            <div class="audit-row"><span class="audit-label">Driver:</span> <span>${fmt(risk.primary_driver)}</span></div>
            <div class="audit-row"><span class="audit-label">Model:</span> <span>Power Outage Risk Model v2.1</span></div>
            <div class="audit-row"><span class="audit-label">Decision ID:</span> <span>${decisionId}</span></div>
        `;
    }
}

function updateRightPanel(risk: RiskSignal, countyName: string) {
    const level = getRiskLevel(risk.risk_score);
    const scoreInt = Math.round(risk.risk_score * 100);
    const rec = recommendations[level];

    // Update score ring
    const circumference = 2 * Math.PI * 34; // r=34
    const offset = circumference - (circumference * scoreInt / 100);
    const ringCircle = document.querySelector('.score-ring circle:nth-child(2)') as SVGCircleElement;
    if (ringCircle) {
        ringCircle.setAttribute('stroke-dashoffset', String(offset));
        const colors: Record<string, string> = { high: '#dc2626', moderate: '#ca8a04', low: '#16a34a' };
        ringCircle.setAttribute('stroke', colors[level]);
    }

    const scoreNum = document.getElementById('score-num');
    const scoreLevel = document.getElementById('score-level');
    if (scoreNum) scoreNum.textContent = String(scoreInt);
    if (scoreLevel) {
        const labels: Record<string, string> = { high: 'CRITICAL RISK', moderate: 'ELEVATED RISK', low: 'NOMINAL' };
        scoreLevel.textContent = labels[level];
        scoreLevel.className = 'score-level ' + (level === 'high' ? 'critical' : level);
    }

    const primaryRoute = document.getElementById('primary-route');
    const altRoute = document.getElementById('alt-route');
    const narrative = document.getElementById('rec-narrative');
    if (primaryRoute) primaryRoute.innerHTML = rec.primary;
    if (altRoute) altRoute.innerHTML = rec.alt;
    if (narrative) narrative.textContent = risk.recommendation || rec.narrative;

    // Action buttons
    const buttons = document.querySelectorAll('.action-btn');
    buttons.forEach(btn => {
        btn.classList.toggle('active', (btn as HTMLElement).dataset.action === rec.action);
    });

    // County detail panel
    const detail = document.getElementById('county-detail');
    const cName = document.getElementById('county-name');
    const cStats = document.getElementById('county-stats');
    if (detail && cName && cStats) {
        detail.style.display = 'block';
        cName.textContent = countyName + ' County';
        cStats.innerHTML = `
            <div class="stat-row"><span class="stat-label">Risk Score</span><span>${risk.risk_score}</span></div>
            <div class="stat-row"><span class="stat-label">Level</span><span style="color:${getStrokeColor(level)}">${level.toUpperCase()}</span></div>
            <div class="stat-row"><span class="stat-label">Driver</span><span>${fmt(risk.primary_driver)}</span></div>
            <div class="stat-row"><span class="stat-label">Est. Impact</span><span>${risk.estimated_impact}</span></div>
            <div class="stat-row"><span class="stat-label">Radius</span><span>${risk.geo_center.impact_radius_km} km</span></div>
        `;
    }

    // Update evidence chain
    updateEvidencePanel(risk, countyName);
}

interface Highway {
    name: string;
    type: string;
    waypoints: number[][];
}

// Find which county a point falls in by nearest center
function findNearestCounty(lat: number, lng: number, risks: RiskSignal[]): RiskSignal | null {
    let best: RiskSignal | null = null;
    let bestDist = Infinity;
    for (const r of risks) {
        const d = Math.pow(lat - r.geo_center.lat, 2) + Math.pow(lng - r.geo_center.lon, 2);
        if (d < bestDist) { bestDist = d; best = r; }
    }
    return best;
}

function getSegmentRiskLevel(p1: number[], p2: number[], risks: RiskSignal[]): string {
    const midLat = (p1[0] + p2[0]) / 2;
    const midLng = (p1[1] + p2[1]) / 2;
    const county = findNearestCounty(midLat, midLng, risks);
    if (!county) return 'low';
    return getRiskLevel(county.risk_score);
}

function getHighwayOverallRisk(hwy: Highway, risks: RiskSignal[]): string {
    let maxScore = 0;
    for (const wp of hwy.waypoints) {
        const county = findNearestCounty(wp[0], wp[1], risks);
        if (county && county.risk_score > maxScore) maxScore = county.risk_score;
    }
    return getRiskLevel(maxScore);
}

async function initMap(risks: RiskSignal[]) {
    try {
        const { Map } = await google.maps.importLibrary("maps") as google.maps.MapsLibrary;
        const map = new Map(document.getElementById("map") as HTMLElement, {
            center: { lat: 37.2, lng: -119.5 },
            zoom: 6,
            mapId: "DEMO_MAP_ID",
        });

        const riskMap = buildRiskMap(risks);
        let activeInfoWindow: google.maps.InfoWindow | null = null;

        // --- County polygons ---
        const geoRes = await fetch('/ca-counties.geojson');
        const geoData = await geoRes.json();

        geoData.features.forEach((feature: any) => {
            const countyName: string = feature.properties.name;
            const risk = riskMap.get(countyName);
            const level = risk ? getRiskLevel(risk.risk_score) : 'low';
            const fillColor = getRiskColor(level);
            const strokeColor = getStrokeColor(level);

            const coords = feature.geometry.coordinates;
            const polygons = feature.geometry.type === 'MultiPolygon' ? coords : [coords];

            polygons.forEach((polygon: number[][][]) => {
                const paths = polygon[0].map((coord: number[]) => ({
                    lat: coord[1], lng: coord[0]
                }));

                const poly = new google.maps.Polygon({
                    paths, strokeColor, strokeOpacity: 0.6, strokeWeight: 1,
                    fillColor, fillOpacity: 0.3,
                    map: map as unknown as google.maps.Map,
                });

                const infoWindow = new google.maps.InfoWindow();
                poly.addListener('click', (e: google.maps.MapMouseEvent) => {
                    if (activeInfoWindow) activeInfoWindow.close();
                    if (risk) updateRightPanel(risk, countyName);
                    const content = risk
                        ? `<div class="info-window">
                            <h4>${countyName} County</h4>
                            <p><strong>Risk:</strong> ${level.toUpperCase()} (${risk.risk_score})</p>
                            <p><strong>Driver:</strong> ${fmt(risk.primary_driver)}</p>
                           </div>`
                        : `<div class="info-window"><h4>${countyName} County</h4><p>No data</p></div>`;
                    infoWindow.setContent(content);
                    if (e.latLng) infoWindow.setPosition(e.latLng);
                    infoWindow.open(map as unknown as google.maps.Map);
                    activeInfoWindow = infoWindow;
                });
                poly.addListener('mouseover', () => poly.setOptions({ fillOpacity: 0.5, strokeWeight: 2 }));
                poly.addListener('mouseout', () => poly.setOptions({ fillOpacity: 0.3, strokeWeight: 1 }));
            });
        });

        // --- Highways ---
        const hwyRes = await fetch('/api/highways');
        const highways: Record<string, Highway> = await hwyRes.json();

        for (const [hwyId, hwy] of Object.entries(highways)) {
            // Draw each segment with its own risk color
            for (let i = 0; i < hwy.waypoints.length - 1; i++) {
                const p1 = hwy.waypoints[i];
                const p2 = hwy.waypoints[i + 1];
                const segLevel = getSegmentRiskLevel(p1, p2, risks);
                const segColor = getStrokeColor(segLevel);

                const segPath = [
                    { lat: p1[0], lng: p1[1] },
                    { lat: p2[0], lng: p2[1] }
                ];

                // White outline for visibility
                new google.maps.Polyline({
                    path: segPath,
                    strokeColor: '#ffffff',
                    strokeOpacity: 0.15,
                    strokeWeight: 6,
                    map: map as unknown as google.maps.Map,
                    zIndex: 5,
                });

                const line = new google.maps.Polyline({
                    path: segPath,
                    strokeColor: segColor,
                    strokeOpacity: 0.9,
                    strokeWeight: 3.5,
                    map: map as unknown as google.maps.Map,
                    zIndex: 10,
                });

                // Click on highway segment
                const infoWindow = new google.maps.InfoWindow();
                line.addListener('click', (e: google.maps.MapMouseEvent) => {
                    if (activeInfoWindow) activeInfoWindow.close();
                    const overallLevel = getHighwayOverallRisk(hwy, risks);
                    const levelColor = getStrokeColor(overallLevel);
                    const content = `<div class="info-window">
                        <h4>${hwy.name}</h4>
                        <p><strong>Segment Risk:</strong> <span style="color:${segColor}">${segLevel.toUpperCase()}</span></p>
                        <p><strong>Overall Route:</strong> <span style="color:${levelColor}">${overallLevel.toUpperCase()}</span></p>
                        <p><strong>Type:</strong> ${hwy.type.replace(/_/g, ' ')}</p>
                    </div>`;
                    infoWindow.setContent(content);
                    if (e.latLng) infoWindow.setPosition(e.latLng);
                    infoWindow.open(map as unknown as google.maps.Map);
                    activeInfoWindow = infoWindow;

                    // Update right panel with highway info
                    updateHighwayPanel(hwy, overallLevel, risks);
                });

                line.addListener('mouseover', () => line.setOptions({ strokeWeight: 6, strokeOpacity: 1 }));
                line.addListener('mouseout', () => line.setOptions({ strokeWeight: 3.5, strokeOpacity: 0.9 }));
            }

            // Highway label at midpoint
            const mid = hwy.waypoints[Math.floor(hwy.waypoints.length / 2)];
            const labelDiv = document.createElement('div');
            labelDiv.className = 'hwy-label';
            labelDiv.textContent = hwyId;

            const { AdvancedMarkerElement } = await google.maps.importLibrary("marker") as google.maps.MarkerLibrary;
            new AdvancedMarkerElement({
                map: map as unknown as google.maps.Map,
                position: { lat: mid[0], lng: mid[1] },
                content: labelDiv,
            });
        }

    } catch (e) {
        console.error("Map initialization failed.", e);
    }
}

function updateHighwayPanel(hwy: Highway, overallLevel: string, risks: RiskSignal[]) {
    const scoreMap: Record<string, number> = { high: 90, moderate: 55, low: 15 };
    const scoreInt = scoreMap[overallLevel];
    const rec = recommendations[overallLevel];

    const circumference = 2 * Math.PI * 34;
    const offset = circumference - (circumference * scoreInt / 100);
    const ringCircle = document.querySelector('.score-ring circle:nth-child(2)') as SVGCircleElement;
    if (ringCircle) {
        ringCircle.setAttribute('stroke-dashoffset', String(offset));
        const colors: Record<string, string> = { high: '#dc2626', moderate: '#ca8a04', low: '#16a34a' };
        ringCircle.setAttribute('stroke', colors[overallLevel]);
    }

    const scoreNum = document.getElementById('score-num');
    const scoreLevel = document.getElementById('score-level');
    if (scoreNum) scoreNum.textContent = String(scoreInt);
    if (scoreLevel) {
        const labels: Record<string, string> = { high: 'CRITICAL RISK', moderate: 'ELEVATED RISK', low: 'NOMINAL' };
        scoreLevel.textContent = labels[overallLevel];
        scoreLevel.className = 'score-level ' + (overallLevel === 'high' ? 'critical' : overallLevel);
    }

    const primaryRoute = document.getElementById('primary-route');
    const altRoute = document.getElementById('alt-route');
    const narrative = document.getElementById('rec-narrative');
    if (primaryRoute) primaryRoute.innerHTML = `${hwy.name} (Status: <span class="text-${overallLevel === 'high' ? 'red' : overallLevel === 'moderate' ? 'yellow' : 'green'}">${overallLevel.toUpperCase()}</span>)`;
    if (altRoute) altRoute.innerHTML = rec.alt;
    if (narrative) narrative.textContent = rec.narrative;

    const buttons = document.querySelectorAll('.action-btn');
    buttons.forEach(btn => btn.classList.toggle('active', (btn as HTMLElement).dataset.action === rec.action));

    // Show segment breakdown in county detail
    const detail = document.getElementById('county-detail');
    const cName = document.getElementById('county-name');
    const cStats = document.getElementById('county-stats');
    if (detail && cName && cStats) {
        detail.style.display = 'block';
        cName.textContent = hwy.name + ' — Segment Analysis';

        let segHtml = '';
        const seen = new Set<string>();
        for (const wp of hwy.waypoints) {
            const county = findNearestCounty(wp[0], wp[1], risks);
            if (county) {
                const ctyName = county.location.replace(/_County$/, '').replace(/_/g, ' ');
                if (!seen.has(ctyName)) {
                    seen.add(ctyName);
                    const lvl = getRiskLevel(county.risk_score);
                    segHtml += `<div class="stat-row"><span class="stat-label">${ctyName}</span><span style="color:${getStrokeColor(lvl)}">${lvl.toUpperCase()} (${county.risk_score})</span></div>`;
                }
            }
        }
        cStats.innerHTML = segHtml;
    }

    // Update evidence chain with highest-risk county on this highway
    let worstRisk: RiskSignal | null = null;
    let worstName = '';
    for (const wp of hwy.waypoints) {
        const county = findNearestCounty(wp[0], wp[1], risks);
        if (county && (!worstRisk || county.risk_score > worstRisk.risk_score)) {
            worstRisk = county;
            worstName = county.location.replace(/_County$/, '').replace(/_/g, ' ');
        }
    }
    if (worstRisk) updateEvidencePanel(worstRisk, worstName);
}

async function init() {
    const select = document.getElementById('event-date') as HTMLSelectElement | null;

    async function loadForDate(date: string) {
        try {
            const url = date ? `/api/risks?date=${encodeURIComponent(date)}` : '/api/risks';
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            const risks: RiskSignal[] = await response.json();

            // Rebuild the map on date change (clears previous overlays).
            const mapEl = document.getElementById('map');
            if (mapEl) mapEl.innerHTML = '';
            await initMap(risks);

            // Default: select highest risk county
            const sorted = [...risks].sort((a, b) => b.risk_score - a.risk_score);
            if (sorted.length > 0) {
                const top = sorted[0];
                const name = top.location.replace(/_County$/, '').replace(/_/g, ' ');
                updateRightPanel(top, name);
            }
        } catch (error) {
            console.error("Failed to load application data:", error);
        }
    }

    // Populate date picker from available dates in the model data.
    let defaultDate = '';
    try {
        const res = await fetch('/api/dates');
        if (res.ok) {
            const { dates, default: def } = await res.json() as { dates: string[]; default: string };
            defaultDate = dates.includes(def) ? def : (dates[0] || '');
            if (select) {
                select.innerHTML = dates.map(d =>
                    `<option value="${d}"${d === defaultDate ? ' selected' : ''}>${new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</option>`
                ).join('');
                select.addEventListener('change', () => loadForDate(select.value));
            }
        }
    } catch (e) {
        console.error('Failed to load date list:', e);
    }

    await loadForDate(defaultDate);
}

window.addEventListener('DOMContentLoaded', init);
