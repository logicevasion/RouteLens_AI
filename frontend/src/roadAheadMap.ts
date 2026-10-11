export const roadAheadSourceId = 'routelens-road-ahead';
const roadAheadLayerIds = [
  'routelens-road-ahead-fill',
  'routelens-road-ahead-line',
  'routelens-road-ahead-selected-fill',
  'routelens-road-ahead-selected-casing',
  'routelens-road-ahead-selected-line',
] as const;

type RoadAheadMap = {
  getLayer: (id: string) => unknown;
  removeLayer: (id: string) => void;
  getSource: (id: string) => unknown;
  removeSource: (id: string) => void;
  addSource: (id: string, source: { type: 'geojson'; data: FeatureCollection }) => void;
};

type RoadAheadSource = { type: string; setData: (data: FeatureCollection) => void };

/** Removes the complete Road Ahead source lifecycle while preserving route and DriveBC layers. */
export function clearRoadAheadMapState(map: RoadAheadMap): void {
  for (const id of [...roadAheadLayerIds].reverse()) {
    if (map.getLayer(id)) map.removeLayer(id);
  }
  if (map.getSource(roadAheadSourceId)) map.removeSource(roadAheadSourceId);
}

export function syncRoadAheadSource(map: RoadAheadMap, data: FeatureCollection): void {
  if (data.features.length === 0) {
    clearRoadAheadMapState(map);
    return;
  }
  const source = map.getSource(roadAheadSourceId) as RoadAheadSource | undefined;
  if (source?.type === 'geojson') source.setData(data);
  else if (!source) map.addSource(roadAheadSourceId, { type: 'geojson', data });
}
import type { FeatureCollection } from 'geojson';
