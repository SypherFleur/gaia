# Units And Comparability

Mercator preserves source-native values and unit context before any comparison.

Each market value retains:

- original value;
- original unit;
- normalized value, only when defensible;
- normalized unit;
- package;
- grade;
- quality;
- currency;
- currency date or context.

GAIA must not silently compare `$/box` with `$/lb` unless package weight and grade context make the conversion defensible. If units, grade, quality, or package are incompatible, the comparison result is `comparable: false` with an explicit reason.

Commodity normalization is separate from unit normalization. `Tomatoes, fresh market`, `TOMATOES`, `Fresh tomatoes`, and `Solanum lycopersicum` may map to the canonical commodity `tomato`, but source-native labels remain attached.

