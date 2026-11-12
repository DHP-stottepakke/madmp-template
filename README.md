# Machine-Actionable DMP

Template based on the [RDA DMP Common Standard (DCS)](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard) for machine-actionable Data Management Plans. It produces maDMPs in JSON according to the [DCS JSON schemas](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema) and the [OSTrails Application Profile](https://github.com/OSTrails/ostrails-madmp-ap). Template is designed for use in [Data Stewardship Wizard](https://ds-wizard.org) 5.0 or newer (for older versions, use the template version 1.x) with [*Common Data Stewardship knowledge model*](https://registry.ds-wizard.org/knowledge-models/dsw:root:latest) and [*Life Sciences DSW Knowledge Model*](https://registry.ds-wizard.org/knowledge-models/dsw:lifesciences:latest), version 2.8.1 or newer (for knowledge models 2.7, use the template version 2.0.0).


## Formats

| Format | Schema |
|---|---|
| JSON (DCS 1.3) | [RDA DMP Common Standard 1.3](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema/1.3) |
| JSON (DCS 1.2) | [RDA DMP Common Standard 1.2](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema/1.2) |
| JSON (DCS 1.1) | [RDA DMP Common Standard 1.1](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema/1.1) (the former JSON format) |
| JSON (DCS 1.0) | [RDA DMP Common Standard 1.0](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard/tree/master/examples/JSON/JSON-schema/1.0) |
| JSON (OSTrails AP) | [OSTrails Application Profile](https://github.com/OSTrails/ostrails-madmp-ap) (DCS 1.2 with extensions) |

Each format contains only what its schema defines; for example, affiliations, project identifiers and reused datasets are available since DCS 1.2, and DCS 1.0 requires project dates and grant identifiers (projects and fundings without them are left out). A DMP is valid only when it has a contact (a contributor with the Contact Person role and an e-mail, or at least a contributor with an e-mail) and, for DCS 1.0, at least one dataset.


## Usage

This template is available through [DSW Registry](https://registry.ds-wizard.org/templates).


## Issues and Contributing

This document template for DSW is available as open-source via GitHub Repository [ds-wizard/madmp-template](https://github.com/ds-wizard/madmp-template), you can [report issues](https://github.com/ds-wizard/madmp-template/issues) there and fork it for customisations or contributions.


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

Starting v1.30.0, AI tools (Codex, Claude Code) are used to assist in the development of this template. The AI tools are used to generate text, fix typos, and improve grammar. The AI tools are used to assist the human contributors in the development of the template.

## Changelog

### 3.1.1

- Fixed the document failing ("'dict object' has no attribute ...") for projects with selected question tags; questions hidden by the tags are treated as not answered
- Fixed the document failing on a contributor whose typed reply ends with "ORCID:"

### 3.1.0

- Added the ethical approval of research projects (approval status and case number) to ethical issues
- Added rights of the datasets from the rights of the collected data and their use restrictions (DCS 1.2 and newer)
- Added related identifiers of the datasets: the paper a dataset supplements and its qualified references to other datasets (DCS 1.2 and newer)
- Fixed DMPs without a contact when no contributor has a role: a person with a name and an e-mail is the contact
- Updated Czech translation

### 3.0.0

- Read replies by knowledge model annotations (`json.key`, `json.value`) instead of UUIDs; requires knowledge models 2.8.1 and newer
- Fixed answers left from a changed or cleared reply (e.g. of GDPR considerations, or of a non-reference data set that will not be used) being exported

### 2.0.0

- Updated to metamodel version 19.0 (Wizard 5.0); the template ID is now `dsw.rda-madmp`
- Added formats for all versions of the RDA DMP Common Standard JSON schema (1.0, 1.1, 1.2, 1.3) and the OSTrails Application Profile; the former JSON format is now JSON (DCS 1.1)
- Removed RDF formats (Turtle, N3, RDF/XML, JSON-LD, N-Triples, TriG)
- Added dataset type and preservation statement, and the repository as distribution host (with its homepage and FAIRsharing DOI)
- Added affiliations (ROR), project identifiers and reused datasets (DCS 1.2 and newer), project acronym and DMP version (OSTrails)
- Used `restricted` instead of the deprecated `shared` data access (DCS 1.3)

### 1.30.0

- Supported template localization (document template locales, metamodel version 18.3, released in DSW 4.35.0): all texts of the maDMP (description, ethical issues, costs) are translatable, codes and contributor roles stay in English
- Added Czech test translation (`locales/cs.po`)
- Set `language` of the DMP according to the locale of the document (ISO 639-3, e.g. `ces`), `eng` without a locale
- Fixed integration values (e.g. funder names) being HTML-escaped (`&amp;`)

### 1.29.0

- Fixed ethical issues that were never exported: legal basis and consent of collected personal data, DPIA, ethical legislation and review, privacy restrictions, pseudonymisation, anonymisation and aggregation
- Fixed `ethical_issues_exist` to be `unknown` when the questions are not answered yet
- Added fallback contact (the first contributor with an e-mail) when no contributor has the Contact Person role
- Fixed funder identifier type (`fundref` for Crossref Funder Registry, `other` for names) and grant identifier type
- Fixed datasets without an identifier (identified by their item UUID instead of an empty string)
- Fixed costs: title fallback, decimal amounts, currency entered as text, description spacing
- Fixed projects without start or end date being omitted
- Fixed contributors with an unparsable ORCID being omitted
- Fixed Turtle (no blank nodes): invalid IRIs, merged dataset nodes, links from projects to fundings, type of contributor identifiers
- Fixed content type of Turtle output (`text/turtle`)

### 1.28.1

- Fixed text value type questions rendering with markdown

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
