import express from 'express';
import cors from 'cors';
import fs from 'fs/promises';
import path from 'path';

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.get('/favicon.ico', (req, res) => res.status(204).end());
app.use(express.static(path.join(__dirname, '../public')));
// Serve compiled client JS from dist (where tsc puts it)
app.use('/js', express.static(path.join(__dirname, '../dist')));

// Paths
// src/server.ts -> compiled to dist/server.js.  dist/ is one level deep in web/.
// So ../../../data/... from dist/server.js
const SIGNALS_DIR = path.resolve(__dirname, '../../../data/input/signals');
const MODEL_CSV = path.resolve(
    __dirname,
    '../../../data/input/registered_provider/OSCCT_risk_model/power_outage/dec2022_mar2023/OSCCT_risk_predict_model.csv'
);

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
    recommendation: string;
    timestamp: string;
    geo_center: GeoCenter;
}

// ---- County metadata cache (geo_center + driver templates from signal files) ----
interface CountyMeta {
    location: string;
    primary_driver: string;
    estimated_impact: string;
    recommendation: string;
    hour: string; // hour-part from the template timestamp, e.g. "05:00:00Z"
    geo_center: GeoCenter;
}

let countyMetaCache: Map<string, CountyMeta> | null = null;

async function loadCountyMeta(): Promise<Map<string, CountyMeta>> {
    if (countyMetaCache) return countyMetaCache;
    const map = new Map<string, CountyMeta>();
    const files = await fs.readdir(SIGNALS_DIR);
    for (const file of files.filter(f => f.endsWith('.json'))) {
        const content = await fs.readFile(path.join(SIGNALS_DIR, file), 'utf-8');
        try {
            const d = JSON.parse(content) as RiskSignal;
            const key = d.location.replace(/_County$/, '').replace(/_/g, ' ');
            const hour = d.timestamp.includes('T') ? d.timestamp.split('T')[1] : '00:00:00Z';
            map.set(key, {
                location: d.location,
                primary_driver: d.primary_driver,
                estimated_impact: d.estimated_impact,
                recommendation: d.recommendation,
                hour,
                geo_center: d.geo_center,
            });
        } catch (e) {
            console.error(`Error parsing ${file}:`, e);
        }
    }
    countyMetaCache = map;
    return map;
}

// ---- CSV cache: date -> county -> score ----
interface DayScores { [county: string]: number; }
let csvCache: Map<string, DayScores> | null = null;
let csvDates: string[] = [];

async function loadCsv(): Promise<{ byDate: Map<string, DayScores>; dates: string[] }> {
    if (csvCache) return { byDate: csvCache, dates: csvDates };
    const content = await fs.readFile(MODEL_CSV, 'utf-8');
    const lines = content.split(/\r?\n/).filter(l => l.trim().length > 0);
    const header = lines[0].split(',');
    const cIdx = header.indexOf('county_name');
    const dIdx = header.indexOf('date');
    const sIdx = header.indexOf('risk score');
    const pIdx = header.indexOf('predicted_risk_score');

    const byDate = new Map<string, DayScores>();
    for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(',');
        const county = cols[cIdx];
        const date = cols[dIdx];
        // Prefer the model prediction (used to populate the demo signal files);
        // fall back to the observed "risk score" when prediction is missing.
        const rawScore = cols[pIdx] !== '' && cols[pIdx] !== undefined ? cols[pIdx] : cols[sIdx];
        const score = parseFloat(rawScore);
        if (!county || !date || isNaN(score)) continue;
        if (!byDate.has(date)) byDate.set(date, {});
        byDate.get(date)![county] = score;
    }
    csvCache = byDate;
    csvDates = Array.from(byDate.keys()).sort();
    return { byDate: csvCache, dates: csvDates };
}

// ---- API: list of selectable event dates ----
app.get('/api/dates', async (_req, res) => {
    try {
        const { dates } = await loadCsv();
        res.json({ dates, default: '2023-01-07' });
    } catch (e) {
        console.error('Error loading dates:', e);
        res.status(500).json({ error: 'Failed to load dates' });
    }
});

// ---- API: risk signals for a given date ----
app.get('/api/risks', async (req, res) => {
    try {
        const meta = await loadCountyMeta();
        const { byDate, dates } = await loadCsv();

        const requested = (req.query.date as string) || '';
        const date = byDate.has(requested) ? requested : (dates.includes('2023-01-07') ? '2023-01-07' : dates[0]);
        const day = byDate.get(date) || {};

        const risks: RiskSignal[] = [];
        for (const [countyName, m] of meta.entries()) {
            const score = day[countyName];
            // If no score for this county/date, treat as 0 (no risk) so the county still renders.
            const risk_score = typeof score === 'number' ? Math.round(score * 100) / 100 : 0;
            risks.push({
                risk_score,
                location: m.location,
                primary_driver: m.primary_driver,
                estimated_impact: m.estimated_impact,
                recommendation: m.recommendation,
                timestamp: `${date}T${m.hour}`,
                geo_center: m.geo_center,
            });
        }
        res.json(risks);
    } catch (error) {
        console.error('Error reading signal files:', error);
        res.status(500).json({ error: 'Failed to retrieve risk data' });
    }
});

// API Endpoint: Highways
const HIGHWAYS_PATH = path.resolve(__dirname, '../../../data/input/highways.json');

app.get('/api/highways', async (_req, res) => {
    try {
        const content = await fs.readFile(HIGHWAYS_PATH, 'utf-8');
        res.json(JSON.parse(content));
    } catch (error) {
        res.status(500).json({ error: 'Failed to load highway data' });
    }
});

// API Endpoint: Evidence / decision template
const TEMPLATE_PATH = path.resolve(__dirname, '../../../data/output/ui_output_template.json');

app.get('/api/evidence', async (_req, res) => {
    try {
        const content = await fs.readFile(TEMPLATE_PATH, 'utf-8');
        res.json(JSON.parse(content));
    } catch (error) {
        res.status(500).json({ error: 'Failed to load evidence data' });
    }
});

app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
    console.log(`Serving static files from public/ and dist/`);
});
