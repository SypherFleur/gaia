# National Weather Service

Last verification date: 2026-08-11.

Source URL: https://www.weather.gov/documentation/services-web-api

Purpose:

- U.S. forecast and alert context.

Fields used:

- point-to-grid lookup;
- forecast valid time;
- generated/retrieved time;
- temperature;
- precipitation probability;
- relative humidity where available;
- wind speed/direction;
- alerts boundary prepared for later use.

Cost:

- Free/open U.S. government service.

Credentials:

- No API key currently required.
- A configured `User-Agent` is required by NWS.

Quota:

- NWS documents reasonable rate limits but does not publish a fixed limit.

Cache behavior:

- Short TTL for forecasts.
- Stale-if-error may be used for low/moderate-risk context only when clearly marked stale.

Data semantics:

- Forecast grid data is not a direct sensor reading.
- Forecast endpoints are discovered through `/points/{latitude},{longitude}`.

Geographic limitations:

- U.S. NWS coverage.

Failure behavior:

- Provider errors produce partial `EnvironmentalSnapshot` output when other sources are available.

Licensing/attribution:

- U.S. government open data; attribute NOAA/National Weather Service.

