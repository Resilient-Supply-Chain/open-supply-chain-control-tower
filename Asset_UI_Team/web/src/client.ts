/// <reference types="google.maps" />

interface GeoCenter { lat: number; lon: number; impact_radius_km: number; }
interface RiskSignal {
    risk_score: number; location: string; primary_driver: string;
    estimated_impact: string; geo_center: GeoCenter;
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

// Recommendations per risk level
const recommendations: Record<string, { action: string; narrative: string; primary: string; alt: string }> = {
    high: {
        action: 'reroute',
        primary: 'Current corridor status: <span class="text-red">High Risk</span>',
        alt: 'Alternate route status: <span class="text-yellow">Moderate Risk</span>',
        narrative: 'Immediate rerouting recommended. Critical infrastructure disruption detected. Stage emergency assets at nearest distribution hub and notify downstream stakeholders.'
    },
    moderate: {
        action: 'stage',
        primary: 'Current corridor status: <span class="text-yellow">Moderate Risk</span>',
        alt: 'Alternate route status: <span class="text-green">Low Risk</span>',
        narrative: 'Elevated risk detected. Pre-stage contingency assets and monitor conditions. Prepare reroute plan if risk escalates within next 12 hours.'
    },
    low: {
        action: 'hold',
        primary: 'Current corridor status: <span class="text-green">Low Risk</span>',
        alt: 'No alternate route needed',
        narrative: 'Conditions nominal. Continue standard operations. Next automated assessment in 6 hours.'
    }
};

// Evidence chain templates per risk level
interface EvidenceCard { icon: string; title: string; body: string; source: string; cls?: string; }

function getEvidenceCards(risk: RiskSignal, countyName: string): EvidenceCard[] {
    const level = getRiskLevel(risk.risk_score);
    const driver = fmt(risk.primary_driver);
    const score = risk.risk_score;
    const now = new Date().toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });

    if (level === 'high') {
        return [
            { icon: '🔴', title: 'RISK DETECTION', body: `${countyName} County flagged at ${score} risk score. Primary driver: ${driver}. Threshold exceeded (>0.8).`, source: `(Risk Engine, ${now})` },
            { icon: '📊', title: 'IMPACT ANALYSIS', body: `Estimated economic impact: ${risk.estimated_impact.replace(/_/g, ' ')}. Affected radius: ${risk.geo_center.impact_radius_km} km. Critical supply routes compromised.`, source: `(Impact Model v2.1, ${now})` },
            { icon: '⚠️', title: 'INFRASTRUCTURE STATUS', body: `${driver} conditions confirmed in ${countyName} region. Local utility and transport disruptions reported. Grid capacity at critical levels.`, source: `(Infrastructure Monitor, ${now})`, cls: 'warn' },
            { icon: '🔄', title: 'SUPPLY CHAIN IMPACT', body: `Downstream SMEs in ${countyName} at risk of delivery delays. Recommend activating contingency suppliers and alternate logistics corridors.`, source: `(Supply Chain Analyzer, ${now})`, cls: 'warn' },
            { icon: '🧠', title: 'RECOMMENDATION', body: `REROUTE immediately. Divert shipments away from ${countyName} corridor. Stage emergency inventory at nearest unaffected distribution hub.`, source: `(Decision Engine v2.1, ${now})`, cls: 'decision' },
        ];
    } else if (level === 'moderate') {
        return [
            { icon: '🟡', title: 'RISK DETECTION', body: `${countyName} County at ${score} risk score. Primary driver: ${driver}. Elevated but below critical threshold.`, source: `(Risk Engine, ${now})` },
            { icon: '📊', title: 'IMPACT ANALYSIS', body: `Estimated impact: ${risk.estimated_impact.replace(/_/g, ' ')}. Monitoring radius: ${risk.geo_center.impact_radius_km} km. Partial disruption possible within 24h.`, source: `(Impact Model v2.1, ${now})` },
            { icon: '📡', title: 'MONITORING STATUS', body: `${driver} conditions developing in ${countyName}. Sensors indicate gradual escalation. No confirmed outages yet.`, source: `(Sensor Network, ${now})` },
            { icon: '📦', title: 'SUPPLY CHAIN STATUS', body: `Pre-stage contingency assets for ${countyName} corridor. Notify tier-1 suppliers of potential delays. Review backup routes.`, source: `(Supply Chain Analyzer, ${now})` },
            { icon: '🧠', title: 'RECOMMENDATION', body: `STAGE assets and monitor. Prepare reroute plan for ${countyName} if conditions escalate. Re-assess in 12 hours.`, source: `(Decision Engine v2.1, ${now})` },
        ];
    } else {
        return [
            { icon: '🟢', title: 'RISK DETECTION', body: `${countyName} County at ${score} risk score. No significant risk drivers detected. All systems nominal.`, source: `(Risk Engine, ${now})` },
            { icon: '📊', title: 'IMPACT ANALYSIS', body: `Minimal estimated impact: ${risk.estimated_impact.replace(/_/g, ' ')}. No disruption expected in the ${risk.geo_center.impact_radius_km} km monitoring zone.`, source: `(Impact Model v2.1, ${now})` },
            { icon: '✅', title: 'INFRASTRUCTURE STATUS', body: `All infrastructure in ${countyName} operating within normal parameters. Grid stable, transport corridors clear.`, source: `(Infrastructure Monitor, ${now})` },
            { icon: '📦', title: 'SUPPLY CHAIN STATUS', body: `Supply routes through ${countyName} fully operational. No action required for current logistics plans.`, source: `(Supply Chain Analyzer, ${now})` },
            { icon: '🧠', title: 'RECOMMENDATION', body: `HOLD current operations. ${countyName} corridor is clear. Next automated assessment in 6 hours.`, source: `(Decision Engine v2.1, ${now})` },
        ];
    }
}

function updateEvidencePanel(risk: RiskSignal, countyName: string) {
    const cards = getEvidenceCards(risk, countyName);
    const container = document.getElementById('evidence-cards');
    if (!container) return;

    container.innerHTML = cards.map(c =>
        `<div class="ev-card ${c.cls || ''}">
            <div class="ev-icon">${c.icon}</div>
            <div class="ev-title">${c.title}</div>
            <div class="ev-body">${c.body}</div>
            <div class="ev-source">${c.source}</div>
        </div>`
    ).join('');

    // Update audit trail
    const level = getRiskLevel(risk.risk_score);
    const auditTs = document.getElementById('audit-ts');
    const auditList = document.getElementById('audit-list');
    if (auditTs) auditTs.textContent = new Date().toLocaleString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', timeZoneName: 'short' });
    if (auditList) {
        const decisionId = '#' + Math.floor(100000 + Math.random() * 900000);
        auditList.innerHTML = `
            <div class="audit-row"><span class="audit-label">Region:</span> <span>${countyName} County</span></div>
            <div class="audit-row"><span class="audit-label">Timestamp:</span> <span>${new Date().toLocaleString()}</span></div>
            <div class="audit-row"><span class="audit-label">Risk Level:</span> <span style="color:${getStrokeColor(level)};font-weight:600">${level.toUpperCase()} (${risk.risk_score})</span></div>
            <div class="audit-row"><span class="audit-label">Driver:</span> <span>${fmt(risk.primary_driver)}</span></div>
            <div class="audit-row"><span class="audit-label">Model:</span> <span>Risk Model v2.1</span></div>
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
    if (narrative) narrative.textContent = rec.narrative;

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
    try {
        const response = await fetch('/api/risks');
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const risks: RiskSignal[] = await response.json();
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

window.addEventListener('DOMContentLoaded', init);
