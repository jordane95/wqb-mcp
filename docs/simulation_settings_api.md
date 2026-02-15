# Simulation Settings API

Source: `assets/logs/platform_config_raw_probe.json` captured on February 16, 2026.

## Endpoint: `OPTIONS https://api.worldquantbrain.com/simulations`

Top-level response:

```json
{
  "actions": {
    "POST": {
      "id": { "...": "..." },
      "parent": { "...": "..." },
      "children": { "...": "..." },
      "type": { "...": "..." },
      "settings": {
        "type": "nested object",
        "required": true,
        "readOnly": false,
        "label": "Simulation settings",
        "children": {
          "instrumentType": {
            "type": "choice",
            "required": true,
            "readOnly": false,
            "label": "Instrument type",
            "choices": [
              { "value": "EQUITY", "label": "Equity" }
            ]
          },
          "region": {
            "type": "choice",
            "required": true,
            "readOnly": false,
            "label": "Region",
            "choices": {
              "instrumentType": {
                "EQUITY": [
                  { "value": "USA", "label": "USA" },
                  { "value": "GLB", "label": "GLB" },
                  { "value": "EUR", "label": "EUR" },
                  { "value": "ASI", "label": "ASI" },
                  { "value": "CHN", "label": "CHN" },
                  { "value": "AMR", "label": "AMR" },
                  { "value": "IND", "label": "IND" }
                ]
              }
            }
          },
          "universe": {
            "type": "choice",
            "required": true,
            "readOnly": false,
            "label": "Universe",
            "choices": {
              "instrumentType": {
                "EQUITY": {
                  "region": {
                    "USA": [
                      { "value": "TOP3000", "label": "TOP3000" },
                      { "value": "TOP1000", "label": "TOP1000" },
                      { "value": "TOP500", "label": "TOP500" },
                      { "value": "TOP200", "label": "TOP200" }
                    ],
                    "GLB": [
                      { "value": "TOP3000", "label": "TOP3000" },
                      { "value": "MINVOL1M", "label": "MINVOL1M" },
                      { "value": "TOPDIV3000", "label": "TOPDIV3000" }
                    ],
                    "EUR": [
                      { "value": "TOP2500", "label": "TOP2500" },
                      { "value": "TOP1000", "label": "TOP1000" }
                    ]
                  }
                }
              }
            }
          },
          "delay": {
            "type": "choice",
            "required": true,
            "readOnly": false,
            "label": "Delay",
            "choices": {
              "instrumentType": {
                "EQUITY": {
                  "region": {
                    "USA": [{ "value": 1, "label": "1" }, { "value": 0, "label": "0" }],
                    "GLB": [{ "value": 1, "label": "1" }]
                  }
                }
              }
            }
          },
          "neutralization": {
            "type": "choice",
            "required": true,
            "readOnly": false,
            "label": "Neutralization",
            "choices": {
              "instrumentType": {
                "EQUITY": {
                  "region": {
                    "USA": [
                      { "value": "NONE", "label": "None" },
                      { "value": "INDUSTRY", "label": "Industry" },
                      { "value": "SUBINDUSTRY", "label": "Subindustry" }
                    ]
                  }
                }
              }
            }
          },
          "decay": { "type": "integer" },
          "truncation": { "type": "float" },
          "pasteurization": { "type": "choice" },
          "unitHandling": { "type": "choice" },
          "nanHandling": { "type": "choice" },
          "selectionHandling": { "type": "choice" },
          "selectionLimit": { "type": "integer" },
          "maxTrade": { "type": "choice" },
          "language": { "type": "choice" },
          "visualization": { "type": "boolean" },
          "testPeriod": { "type": "string" }
        }
      }
    }
  }
}
```

## Normalized Client Output Schema

This is the response contract produced by `SimulationSettingsMixin.get_platform_setting_options`.

```json
{
  "instrument_options": [
    {
      "InstrumentType": "EQUITY",
      "Region": "USA",
      "Delay": 1,
      "Universe": ["TOP3000", "TOP1000", "TOP500", "TOP200"],
      "Neutralization": ["NONE", "INDUSTRY", "SUBINDUSTRY"]
    },
    {
      "InstrumentType": "EQUITY",
      "Region": "USA",
      "Delay": 0,
      "Universe": ["TOP3000", "TOP1000", "TOP500", "TOP200"],
      "Neutralization": ["NONE", "INDUSTRY", "SUBINDUSTRY"]
    }
  ],
  "total_combinations": 10,
  "instrument_types": ["EQUITY"],
  "regions_by_type": {
    "EQUITY": ["USA", "GLB", "EUR", "ASI", "CHN", "AMR", "IND"]
  }
}
```

## Notes

- The raw API uses nested conditional choices (`choices.instrumentType -> region -> [...]`) instead of a flat table.
- The client intentionally flattens this into one row per `(instrumentType, region, delay)`.
- `Universe` and `Neutralization` are region-level lists repeated across delay rows for that `(instrumentType, region)`.
