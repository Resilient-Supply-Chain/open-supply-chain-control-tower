const fs = require("fs");
const path = require("path");

const data = JSON.parse(
  fs.readFileSync(path.join(__dirname, "data/output/data_series.json"), "utf-8")
);

const countyCoords = {
  "Alameda": { lat: 37.6017, lon: -121.7195 },
  "Alpine": { lat: 38.5941, lon: -119.8207 },
  "Amador": { lat: 38.4466, lon: -120.6533 },
  "Butte": { lat: 39.6667, lon: -121.6008 },
  "Calaveras": { lat: 38.1964, lon: -120.5544 },
  "Colusa": { lat: 39.1776, lon: -122.2375 },
  "Contra Costa": { lat: 37.9535, lon: -121.9500 },
  "Del Norte": { lat: 41.7558, lon: -124.2026 },
  "El Dorado": { lat: 38.7786, lon: -120.5246 },
  "Fresno": { lat: 36.7378, lon: -119.7871 },
  "Glenn": { lat: 39.5985, lon: -122.3927 },
  "Humboldt": { lat: 40.7450, lon: -123.8695 },
  "Imperial": { lat: 33.0114, lon: -115.4734 },
  "Inyo": { lat: 36.5114, lon: -117.4109 },
  "Kern": { lat: 35.3733, lon: -118.9965 },
  "Kings": { lat: 36.0988, lon: -119.8815 },
  "Lake": { lat: 39.0840, lon: -122.8084 },
  "Lassen": { lat: 40.6736, lon: -120.5917 },
  "Los Angeles": { lat: 34.0522, lon: -118.2437 },
  "Madera": { lat: 37.2519, lon: -119.7627 },
  "Marin": { lat: 38.0834, lon: -122.7633 },
  "Mariposa": { lat: 37.5848, lon: -119.9662 },
  "Mendocino": { lat: 39.4380, lon: -123.3907 },
  "Merced": { lat: 37.1948, lon: -120.7220 },
  "Modoc": { lat: 41.5888, lon: -120.7254 },
  "Mono": { lat: 37.9391, lon: -118.8864 },
  "Monterey": { lat: 36.2400, lon: -121.3100 },
  "Napa": { lat: 38.5025, lon: -122.2654 },
  "Nevada": { lat: 39.3013, lon: -120.7688 },
  "Orange": { lat: 33.7175, lon: -117.8311 },
  "Placer": { lat: 39.0916, lon: -120.7180 },
  "Plumas": { lat: 40.0036, lon: -120.8394 },
  "Riverside": { lat: 33.7438, lon: -115.9940 },
  "Sacramento": { lat: 38.5816, lon: -121.4944 },
  "San Benito": { lat: 36.6058, lon: -121.0750 },
  "San Bernardino": { lat: 34.8414, lon: -116.1781 },
  "San Diego": { lat: 32.7157, lon: -117.1611 },
  "San Francisco": { lat: 37.7749, lon: -122.4194 },
  "San Joaquin": { lat: 37.9349, lon: -121.2713 },
  "San Luis Obispo": { lat: 35.3102, lon: -120.3993 },
  "San Mateo": { lat: 37.4337, lon: -122.4014 },
  "Santa Barbara": { lat: 34.7083, lon: -120.0339 },
  "Santa Clara": { lat: 37.3541, lon: -121.9552 },
  "Santa Cruz": { lat: 37.0454, lon: -122.0580 },
  "Shasta": { lat: 40.5865, lon: -122.3917 },
  "Sierra": { lat: 39.5774, lon: -120.5219 },
  "Siskiyou": { lat: 41.5926, lon: -122.5400 },
  "Solano": { lat: 38.2668, lon: -121.9400 },
  "Sonoma": { lat: 38.5780, lon: -122.9888 },
  "Stanislaus": { lat: 37.5591, lon: -120.9876 },
  "Sutter": { lat: 39.0346, lon: -121.6947 },
  "Tehama": { lat: 40.1257, lon: -122.2342 },
  "Trinity": { lat: 40.6514, lon: -123.1136 },
  "Tulare": { lat: 36.2274, lon: -118.7815 },
  "Tuolumne": { lat: 38.0282, lon: -119.9537 },
  "Ventura": { lat: 34.3705, lon: -119.1391 },
  "Yolo": { lat: 38.6864, lon: -121.9018 },
  "Yuba": { lat: 39.2888, lon: -121.3502 }
};

const levelRank = { "high": 3, "moderate": 2, "low": 1 };
const riskScoreRange = {
  "high": [0.82, 0.98],
  "moderate": [0.35, 0.75],
  "low": [0.05, 0.28]
};
const radiusMap = { "high": 30, "moderate": 15, "low": 8 };
const impactMap = { "high": "$25M_Day", "moderate": "$8M_Day", "low": "$1M_Day" };
const driverMap = {
  "Power Outage": ["Grid_Overload", "Transmission_Failure", "Wildfire_Shutoff", "Storm_Damage", "Equipment_Aging"],
  "No Risk": ["Stable_Operations"]
};

// Use a date with good distribution of risk levels
const targetDate = "2022-12-04";
const counties = data[targetDate];

const outDir = path.join(__dirname, "data/input/signals");

let count = 0;
for (const c of counties) {
  const coords = countyCoords[c.name];
  if (!coords) { console.log("Missing coords:", c.name); continue; }

  const level = c.riskLevel;
  const range = riskScoreRange[level] || riskScoreRange["low"];
  const score = Math.round((range[0] + Math.random() * (range[1] - range[0])) * 100) / 100;

  const rType = c.riskType || "No Risk";
  const drivers = driverMap[rType] || ["Unknown"];
  const driver = drivers[Math.floor(Math.random() * drivers.length)];

  const signal = {
    risk_score: score,
    location: c.name.replace(/ /g, "_") + "_County",
    primary_driver: driver,
    estimated_impact: impactMap[level] || "$1M_Day",
    geo_center: { lat: coords.lat, lon: coords.lon, impact_radius_km: radiusMap[level] || 10 }
  };

  const filename = c.name.toLowerCase().replace(/ /g, "_") + "_risk_event.json";
  fs.writeFileSync(path.join(outDir, filename), JSON.stringify(signal, null, 2));
  count++;
}

// Count distribution
let h=0,m=0,l=0;
for (const c of counties) { if(c.riskLevel==="high")h++; else if(c.riskLevel==="moderate")m++; else l++; }
console.log("Generated " + count + " signals: high=" + h + " moderate=" + m + " low=" + l);
