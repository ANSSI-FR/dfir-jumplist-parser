

# Jumplist Parser
[![badge_repo](https://img.shields.io/badge/ANSSI--FR-DFIR--Ogre-white)](https://github.com/ANSSI-FR/dfir-ogre)
[![category_badge_external](https://img.shields.io/badge/category-external-%23b556b6)](https://anssi-fr.github.io/README.en.html#project-categories)
[![openess_badge_A](https://img.shields.io/badge/code.gouv.fr-collaborative-blue)](https://anssi-fr.github.io/README.en.html#openness-level)

Parser for Jumplist used by the [DFIR-OGRE software](https://github.com/ANSSI-FR/dfir-ogre).

## ⚠️ Beta Status
This software is currently in **beta**. While functional and actively developed, it may still undergo breaking changes, and some artefact parsers may not yet be fully stabilized. We welcome feedback, bug reports, and contributions using the [issue tracker](https://github.com/ANSSI-FR/dfir-ogre/issues).

## Installation

```bash
# Using pip
git clone git@github.com:ANSSI-FR/dfir-jumplist-parser.git
pip install dfir-jumplist-parser/
```

## Usage

```bash
jumplist-parser --version
jumplist-parser --help
jumplist-parser 'B012C56012C52BE2_100000000DC26_100000000DC52_4_590aee7bdd69b59b.customDestinations-ms_{00000000-0000-0000-0000-000000000000}.data'
jumplist-parser '2432D67532D64B84_1000000017FE1_10000000182D0_4_f18460fded109990.automaticDestinations-ms_{00000000-0000-0000-0000-000000000000}.data'
jumplist-parser '84B6B902B6B8F5B0_100000001DB7F_100000001DB81_4_02_-_Windows_Terminal.lnk_{00000000-0000-0000-0000-000000000000}.data'
jumplist-parser --split-by-lnk 'B012C56012C52BE2_100000000DC26_100000000DC52_4_590aee7bdd69b59b.customDestinations-ms_{00000000-0000-0000-0000-000000000000}.data'
```

## Usage as module

```python
from pathlib import Path
from jumplist_parser import parse_jumplist

# Generic parser, can parse every jumplist
path = Path("590aee7bdd69b59b.customDestinations-ms")
with path.open("rb") as file:
    jumplist = parse_jumplist(file, path=path)  # Path helps to resolve AppID
```

## Location of these artifacts

- `%APPDATA%/Microsoft/Windows/Recent/AutomaticDestinations`
- `%APPDATA%/Microsoft/Windows/Recent/CustomDestinations`

## Information about special fields

### .modification_time

The interpretation of `modification_time` depends on which jumplist is parsed:

- **automaticDestination-ms**: `max(.lnk[].info.modification_time)`
- **customDestination-ms**: `max(.lnk[].header.modification_time)`
- **lnk**: `.lnk[0].header.modification_time`

### .filesystem.application.name

The `name` of the application is resolved from a custom aggregation of a Database of AppID. It's not stored inside the lnk. See the `scripts/update.py` for more details.

### .lnk[].extra.DISTRIBUTED_LINK_TRACKER_BLOCK

We use the `droid_file_identifier` and `birth_droid_file_identifier` fields for extract timestamp, the mft_seq and mac using the [UUIDv1](https://docs.python.org/3/library/uuid.html#uuid.uuid1) specifications. Once we obtain the mac address, we can use the CSV file provided by [ieee.org](https://standards-ieee.org/assignment/ethereum.html) to resolve the mac vendor.

## French Cybersecurity Agency (ANSSI)
<img src="https://www.sgdsn.gouv.fr/files/styles/ds_image_paragraphe/public/files/Notre_Organisation/logo_anssi.png" alt="ANSSI logo" width="25%">
    
*This projet is managed by [ANSSI](https://cyber.gouv.fr/). To find out more, you can visit the [page](https://cyber.gouv.fr/enjeux-technologiques/open-source/) (in French) dedicated to ANSSI’s open-source strategy. You can also click on the badges above to learn more about their meaning.*
