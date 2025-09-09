export const dmsToDecimal = (dms: string): number | null => {
  try {
    // Nettoyer les caractères spéciaux
    const cleanDms = dms
      .replace(/Â°/g, '°')
      .replace(/\s+/g, '')
      .trim();

    // Format DMS avec symboles (33°31'25.6"N)
    const dmsMatch = cleanDms.match(/^(\d+)°(\d+)'([\d.]+)"([NSEW])$/);
    if (dmsMatch) {
      const [, degrees, minutes, seconds, direction] = dmsMatch;
      const decimal = parseFloat(degrees) +
                     parseFloat(minutes) / 60 +
                     parseFloat(seconds) / 3600;
      return (direction === 'S' || direction === 'W') ? -decimal : decimal;
    }

    // Format décimal simple
    const decimal = parseFloat(cleanDms);
    if (!isNaN(decimal)) {
      return decimal;
    }

    console.warn(`Format de coordonnées non reconnu: ${cleanDms}`);
    return null;
  } catch (error) {
    console.error('Error converting coordinates:', error, 'Input:', dms);
    return null;
  }
};

export const parseCoordinates = (location: string): [number, number] | null => {
  if (!location) return null;
  
  try {
    // Nettoyer les caractères spéciaux et espaces multiples
    const cleanLocation = location
      .replace(/Â°/g, '°')
      .replace(/\s+/g, ' ')
      .trim();

    // Cas 1: Format décimal (33.552084 -7.6576159)
    if (!cleanLocation.includes('°')) {
      const [lat, lng] = cleanLocation.split(/[, \t]+/).map(parseFloat);
      if (!isNaN(lat) && !isNaN(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
        return [lat, lng];
      }
    }

    // Cas 2: Format DMS (33°31'25.6"N 7°29'06.8"W)
    const [latDms, lngDms] = cleanLocation.split(' ');
    const lat = dmsToDecimal(latDms);
    const lng = dmsToDecimal(lngDms);

    if (lat !== null && lng !== null && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
      return [lat, lng];
    }

    console.warn(`Coordonnées invalides ou hors limites: ${cleanLocation}`);
    return null;
  } catch (error) {
    console.error('Error parsing coordinates:', error, 'Location:', location);
    return null;
  }
};

export const decimalToDms = (decimal: number, isLatitude: boolean): string => {
  const absDecimal = Math.abs(decimal);
  const degrees = Math.floor(absDecimal);
  const minutes = Math.floor((absDecimal - degrees) * 60);
  const seconds = ((absDecimal - degrees - minutes / 60) * 3600).toFixed(1);
  const direction = isLatitude 
    ? (decimal >= 0 ? 'N' : 'S')
    : (decimal >= 0 ? 'E' : 'W');
  
  return `${degrees}°${minutes}'${seconds}"${direction}`;
}; 