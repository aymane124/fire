import { FeatureCollection } from 'geojson';

export const marocData: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: {
        ADMIN: 'Morocco',
        POP_EST: 36029138
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [-5.193863, 35.755182],
            [-5.155366, 35.603249],
            [-5.220942, 35.482958],
            [-5.527985, 35.511289],
            [-5.527985, 35.755182],
            [-5.193863, 35.755182]
          ]
        ]
      }
    }
  ]
}; 