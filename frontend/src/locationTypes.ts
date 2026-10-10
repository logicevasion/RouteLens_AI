/** RouteLens canonical location contract shared with the FastAPI API. */
export type Location = {
  name: string;
  latitude: number;
  longitude: number;
  address?: string | null;
  provider_id?: string | null;
};

export type DestinationValidation = {
  valid: boolean;
  reason: string | null;
};
