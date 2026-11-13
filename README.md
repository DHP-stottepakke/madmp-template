# Machine-Actionable DMP

Template based on the [RDA DMP Common Standard (DCS)](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard) for machine-actionable Data Management Plans. It produces maDMPs in JSON according to the [DCS JSON schemas](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema) and the [OSTrails Application Profile](https://github.com/OSTrails/ostrails-madmp-ap). Template is designed for use in [Data Stewardship Wizard](https://ds-wizard.org) 5.0 or newer (for older versions, use the template version 1.x) with the [Norwegian DSW Knowledge Model](https://registry.ds-wizard.org/knowledge-models/research.data.no:norway-generic:latest) (`research.data.no.norway-generic` 1.2.0 or newer).

This is a fork of [ds-wizard/madmp-template](https://github.com/ds-wizard/madmp-template), which targets the Common Data Stewardship and Life Sciences knowledge models. The mapping (`src/_mapping.j2`) is specific to the Norwegian knowledge model; the formats, schema-version handling and localization follow upstream.


## Formats

| Format | Schema |
|---|---|
| JSON (DCS 1.3) | [RDA DMP Common Standard 1.3](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema/1.3) |
| JSON (DCS 1.2) | [RDA DMP Common Standard 1.2](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema/1.2) |
| JSON (DCS 1.1) | [RDA DMP Common Standard 1.1](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema/1.1) (format UUID of the former JSON format) |
| JSON (DCS 1.0) | [RDA DMP Common Standard 1.0](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema/1.0) |
| JSON (OSTrails AP) | [OSTrails Application Profile](https://github.com/OSTrails/ostrails-madmp-ap) (DCS 1.2 with extensions) |

Each format contains only what its schema defines: affiliations, alternate identifiers, reused datasets, rights and host identifiers are available since DCS 1.2; DCS 1.3 uses `restricted` instead of the deprecated `shared` data access; DCS 1.0 requires project dates and grant identifiers (projects and fundings without them are left out). The texts of the maDMP are translatable, and `dmp.language` follows the locale of the document.

Deliberate deviations from the schemas (the output is then not valid, but no information is lost):

- A license is exported also without a starting date (`start_date` is required by all versions).
- A DMP is exported also without datasets (DCS 1.0 requires at least one).


## Usage

This template is available through [DSW Registry](https://registry.ds-wizard.org/templates).


## Issues and Contributing

This document template for DSW is available as open-source via GitHub Repository [DHP-stottepakke/madmp-template](https://github.com/DHP-stottepakke/madmp-template), you can [report issues](https://github.com/DHP-stottepakke/madmp-template/issues) there and fork it for customisations or contributions.


## AI-Assisted Development

Some recent changes in this repository were developed with AI-assisted tooling. Proposed code, template mappings, local tooling, and documentation changes were reviewed and adapted by human contributors before being kept in the repository.

For the work captured in this thread, the following AI tooling was used:

- Agent: GitHub Copilot coding agent
- Models: Claude Opus 4.7, GPT-5.4


### Contributors

* **Marek Suchánek** <[marek.suchanek@ds-wizard.org](mailto:marek.suchanek@ds-wizard.org)>
  * ORCID: [0000-0001-7525-9218](https://orcid.org/0000-0001-7525-9218)
  * GitHub: [@MarekSuchanek](https://github.com/MarekSuchanek)
* **Kryštof Komanec** <[krystof.komanec@ds-wizard.org](mailto:krystof.komanec@ds-wizard.org)>
  * ORCID: [0000-0003-3856-1682](https://orcid.org/0000-0003-3856-1682)
  * GitHub: [@krystofkomanec](https://github.com/krystofkomanec)
* **Jana Martínková** <[jana.martinkova@ds-wizard.org](mailto:jana.martinkova@ds-wizard.org)>
  * ORCID: [0000-0001-8575-6533](https://orcid.org/0000-0001-8575-6533)
  * GitHub: [@jmartinkova](https://github.com/jmartinkova)
* **Michael Dondrup** <[mdondrup@gmail.com](mailto:mdondrup@gmail.com)>
  * ORCID: [0000-0002-2371-5928](https://orcid.org/0000-0002-2371-5928)
  * GitHub: [@mdondrup](https://github.com/mdondrup)
* **Korbinian Bösl** <[korbinian.bosl@uib.no](mailto:korbinian.bosl@uib.no)>
  * ORCID: [0000-0003-0498-4273](https://orcid.org/0000-0003-0498-4273)
  * GitHub: [@korbinib](https://github.com/korbinib)



## Changelog


### 2.0.0

- Updated to metamodel version 19.0 (DSW 5.0); the template ID is now `research.data.no.rda-madmp` and the allowed package `research.data.no.norway-generic`
- Added formats for all versions of the RDA DMP Common Standard JSON schema (1.0, 1.1, 1.2, 1.3) and the OSTrails Application Profile, with the same format UUIDs as [ds-wizard/madmp-template](https://github.com/ds-wizard/madmp-template); the UUID of the former JSON format (DCS 1.2) now belongs to JSON (DCS 1.1), so documents of the former JSON format are generated according to DCS 1.1
- Removed RDF formats (Turtle, N3, RDF/XML, JSON-LD, N-Triples, TriG)
- Marked the texts of the maDMP for translation; the language of the DMP follows the locale of the document (ISO 639-3)
- Added the contact's affiliation (DCS 1.2 and newer) and the DMP version (OSTrails, latest named project version)
- Fixed project abstract and free-text dataset descriptions to be exported without Markdown
- Fixed distributions without data access and hosts without title or URL that made the maDMP invalid
- Replaced the vendored document worker in `tools/` with `dsw-tdk` 5.0 and added schema validation (`tools/check.sh`)
- Tested projects with selected question tags (questions hidden by the tags are treated as not answered); the end-to-end test (`tools/e2e.py`) covers them


### 1.29.1

- Fixed text value type questions rendering with markdown
- Export of additional information following [RDA DCS 1.2](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/releases/tag/v1.2) 

### 1.29.0

- Reworked the maDMP JSON mapping to use annotation-based `extract_replies` navigation instead of UUID-based lookups
- Added compatibility for `research.data.no:norway-generic:1.2.0`
- Simplified the mapping by removing the legacy `_uuids.j2` and `_keys.j2` helper files
- Improved ethical issues export for the current KM answer shapes, including boolean Yes/No handling and free-text details
- Added a local render/test toolchain under `tools/` for strict rendering, reply dumping, and KM inspection

### 1.28.0

- Adjusted template metamodel version to 18.0 (released in DSW 4.29.0)

### 1.27.1

- Adjusted template metamodel version to 17.1 (released in DSW 4.26.0)

### 1.27.0

- Updated reused dataset name to use reply string value instead FAIRsharing integration
- Updated dependency on KM to 2.7.0

### 1.26.0

- Update dependency on KM to 2.6.13
- Fix legacy integration type

### 1.25.0

- Update integrations to metamodel version 17.0 (released in DSW 4.22.0)

### 1.24.0

- Adjusted to template metamodel version 17.0 (released in DSW 4.22.0)

### 1.23.0

- Fix ethical issues related to reuse of non-reference datasets
- Updated minimum required version of compatible knowledge models to 2.6.11
- Updated README with the latest link to the DCS Ontology

### 1.22.0

- Added ORCID integration
- Added compatible knowledge models to README

### 1.21.0

- Improved Authors of the DMP

### 1.20.0

- Adjusted to template metamodel version 16 (released in DSW 4.13.0)

### 1.19.0

- Adjusted to template metamodel version 15 (released in DSW 4.12.0)

### 1.18.0

- Adjusted to template metamodel version 14 (released in DSW 4.10.0)

### 1.17.1

- Fix costs in project: typo in dcso prefix and endings of elements

### 1.17.0

- Add costs in project

### 1.16.0

- Adjusted to template metamodel version 13 (released in DSW 4.3.0)

### 1.15.0

- Adjusted to template metamodel version 12 (released in DSW 4.1.0)

### 1.14.0

- Adjusted to template metamodel version 11 (released in DSW 3.20.0)

### 1.13.1

- Fix defaults to prevent failure "Object of type Undefined is not JSON serializable"

### 1.12.0

- Adjusted to template metamodel version 9 (released in DSW 3.10.0)

### 1.11.0

- Compatible with `dsw:root:2.4.0`

### 1.10.0

- Adjusted to template metamodel version 8 (released in DSW 3.8.0)

### 1.9.0

- Adjusted to template metamodel version 7 (released in DSW 3.7.0)

### 1.8.0

- Adjusted to template metamodel version 6 (released in DSW 3.6.0)

### 1.7.0

- Adjusted to template metamodel version 5 (released in DSW 3.5.0)

### 1.6.0

- Added support for Turtle export without Blank nodes

### 1.5.0

- Adjusted to template metamodel version 4 (released in DSW 3.2.0)

### 1.4.0

- Adjusted to template metamodel version 3 (released in DSW 2.12.0)
- Fix licenses in RDF formats

### 1.3.1

- Fix problem with failing on missing Grant ID

### 1.3.0

- Fix ethical issues with non-reference datasets
- Compatible with `dsw:root:2.3.0`
- Added *data steward* contributor role

### 1.2.0

- Updated according to [RDA DMP Common Standard v1.1](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/releases/tag/v1.1)

### 1.1.0

- Adjusted to template metamodel version 2
- Allow `dsw:lifesciences:2.2.0` and higher

### 1.0.0

- Initial version based on results of [RDA hackathon on maDMPs 2020](https://rda-dmp-common.github.io/hackathon-2020/)
- Compatible with *DCS JSON Schema 1.0* and *DCSO 3.0.2*
