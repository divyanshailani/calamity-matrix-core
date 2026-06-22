export const countryCoords: Record<string, { lat: number; lng: number; zoom: number }> = {
  "USA": { lat: 37.0902, lng: -95.7129, zoom: 3 },
  "Indonesia": { lat: -0.7893, lng: 113.9213, zoom: 4 },
  "Japan": { lat: 36.2048, lng: 138.2529, zoom: 4.5 },
  "China": { lat: 35.8617, lng: 104.1954, zoom: 3 },
  "India": { lat: 20.5937, lng: 78.9629, zoom: 4 },
  "Philippines": { lat: 12.8797, lng: 121.7740, zoom: 5 },
  "Mexico": { lat: 23.6345, lng: -102.5528, zoom: 4 },
  "Turkey": { lat: 38.9637, lng: 35.2433, zoom: 5 },
  "Chile": { lat: -35.6751, lng: -71.5430, zoom: 4 },
};

export const countries = ["USA", "Indonesia", "Japan", "China", "India", "Philippines", "Mexico", "Turkey", "Chile"];
export const disasters = ["Earthquake", "Flood", "Storm", "Wildfire", "Volcanic activity", "Drought", "Extreme temperature"];
export const months = Array.from({ length: 12 }, (_, i) => i + 1);

export const defaultContexts: Record<string, string> = {
  "Earthquake": "A massive earthquake striking a populated urban area.",
  "Flood": "Severe flooding submerging infrastructure and residential zones.",
  "Storm": "Category 5 hurricane bringing destructive winds and storm surges.",
  "Wildfire": "Uncontrolled wildfire rapidly spreading across dry vegetation.",
  "Volcanic activity": "Major volcanic eruption with heavy ashfall and pyroclastic flows.",
  "Drought": "Prolonged severe drought causing catastrophic agricultural failure.",
  "Extreme temperature": "Unprecedented heatwave severely impacting power grids and public health."
};

export const getSeverityLabel = (type: string) => {
  switch(type) {
    case "Earthquake": return "Magnitude (Richter Scale)";
    case "Flood": return "Severity (Water Depth / Area)";
    case "Storm": return "Severity (Category / Wind Speed)";
    case "Wildfire": return "Severity (Burn Area)";
    case "Volcanic activity": return "Severity (VEI / Ash Fall)";
    case "Drought": return "Severity (Duration / Aridity)";
    case "Extreme temperature": return "Severity (Temperature Anomaly)";
    default: return "Severity / Magnitude";
  }
};
