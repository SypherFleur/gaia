# Atlas

Last verification date: 2026-08-11.

Atlas is GAIA's geospatial and jurisdiction foundation. It answers which administrative, watershed, hardiness, economic, regulatory, quarantine, and pest-zone geometries contain a point. Sentinel later interprets what those zones legally mean for movement or compliance decisions.

Inputs:

- latitude
- longitude
- optional timestamp
- privacy precision

Outputs normalize into `GeoContext` with country/country code, state or region, optional state code, county or district, optional FIPS, timezone, elevation, hardiness zone, watershed, optional ecoregion/climate zone, zone arrays, source records, and generated timestamp.

Atlas is provider-neutral. Provider-specific response shapes must not leak into `GeoContext` or API responses.

Coordinate privacy:

- exact coordinates may be used internally when authorized;
- external/shared display coordinates are reduced by privacy precision;
- reduced display values never mutate stored source coordinates;
- exact coordinates must not be sent to remote providers when egress policy forbids exact location egress.

Current implementation:

- fixture geography provider for U.S./Texas/Travis and Singapore administrative structures;
- fixture hardiness provider;
- fixture watershed provider;
- fixture regulatory geometry provider;
- schema support for future jurisdiction/quarantine/pest/economic zone feature records.

