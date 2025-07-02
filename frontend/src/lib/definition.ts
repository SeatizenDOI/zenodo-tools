export const DEFAULT_COORDS = { lat: -21.085198, lng: 55.222047, zoom: 13 };

export type LinkType = {
  link: string;
  name: string;
};

export type EdnaDataType = {
  place: string;
  GPSLatitude: string;
  GPSLongitude: string;
  date: string;
  description: string;
  thumbnail: string;
  publication: LinkType;
  data: LinkType;
};
