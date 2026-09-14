# Provision for unsaved planning variants

`CalculateVariantServicesProvision` is available on both `/effects/mcp` and
`/provision/mcp`. It supplements `CalculateServicesProvision`; existing tool
names and arguments are unchanged.

Required arguments are `scenario_id`, `services` (the usual service ID/name/layer
map) and a positive `target_population`. At least one of the following is needed:

- `generated_buildings`: a WGS84 GeoJSON FeatureCollection from GenBuilder.
  Residential features require `properties.zone = "residential"` and positive
  `floors_count`. Existing scenario buildings are retained. `is_excluded` features
  are ignored because GenBuilder returns them with zeroed attributes; original
  Urban attributes must not be overwritten with those values.
- `additional_services`: a map from requested service type ID to a WGS84
  FeatureCollection of new services. Each feature requires the matching
  `properties.service_type_id` and an explicit positive `capacity`. Existing
  scenario and context services are retained.

The target is the **total population** of the scenario, including existing
residents, not only residents of newly generated buildings. The calculation uses
the existing floor-area restoration, normative demand and gravity accessibility
model. It does not use GenBuilder's resident count as an implicit population
assignment. Negative temporary IDs identify additions without colliding with
existing IDs. No layer is written to Urban API.

Run the baseline separately through `CalculateServicesProvision` with the intended
baseline population. The variant response returns the usual `services` summaries
and optional layers, plus `variant`, `scenario_id`, `target_population` and a
methodology note. Missing Urban service normatives remain explicit errors; this
endpoint does not supply numerical defaults or treat missing norms as compliance.
The summary still covers the existing calculator's combined scenario/context
scope; do not relabel it as a scenario-only statistic.

Consumer coordination: gMART's provision specialist uses artifact references to
pass the full generated data. The new tool is mounted on the existing effects MCP
URL so a separate downstream URL is not needed. Stored tool-chain consumers that
restrict tool names must add this name before replaying variant calls.
