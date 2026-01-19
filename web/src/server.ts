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
// Assuming we are in web/dist/server.js, the data is in ../../../data/signals
// But we run from web/ root, so process.cwd() is web/.
// Let's rely on relative path from this file.
// src/server.ts -> compiled to dist/server.js.
// dist/ is one level deep in web/.
// So ../../../data/signals from dist/server.js
const SIGNALS_DIR = path.resolve(__dirname, '../../data/signals');

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

// API Endpoint
app.get('/api/risks', async (req, res) => {
    try {
        console.log(`Scanning for signals in: ${SIGNALS_DIR}`);
        const files = await fs.readdir(SIGNALS_DIR);
        const jsonFiles = files.filter(f => f.endsWith('.json'));
        
        const risks: RiskSignal[] = [];

        for (const file of jsonFiles) {
            const filePath = path.join(SIGNALS_DIR, file);
            const content = await fs.readFile(filePath, 'utf-8');
            try {
                const data = JSON.parse(content) as RiskSignal;
                // Requirement: Filter where Risk Score is strictly greater than 0.8
                if (data.risk_score > 0.8) {
                    risks.push(data);
                }
            } catch (parseError) {
                console.error(`Error parsing ${file}:`, parseError);
            }
        }

        res.json(risks);
    } catch (error) {
        console.error('Error reading signal files:', error);
        res.status(500).json({ error: 'Failed to retrieve risk data' });
    }
});

app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
    console.log(`Serving static files from public/ and dist/`);
});
