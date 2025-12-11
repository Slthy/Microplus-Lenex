# 🏊 LenexEncoder: Swimming Competition Data Processor

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LENEX 3.0](https://img.shields.io/badge/LENEX-3.0-green)](https://wiki.swimrankings.net/images/6/62/Lenex_3.0_Technical_Documentation.pdf)

A professional, modular OOP system for scraping swimming competition data from timing systems and encoding it to **LENEX 3.0** format — the international standard for swimming data exchange.

> **Version 2.0** — Complete architectural refactoring with extensible design for multiple timing systems and output formats.

---

## ✨ Features

### 🎯 Core Capabilities
- **Web Scraping**: Automatically downloads competition data from Microplus timing systems
- **LENEX 3.0 Encoding**: Exports standards-compliant XML files compatible with all major swimming software
- **FINA Points**: Automatic calculation using 2026 World Aquatics base times
- **Relay Support**: Full support for relay teams with swimmer positions and splits
- **Split Times**: Preserves intermediate split times for all races
- **Age Groups**: Intelligent handling of junior categories and age-based classifications

### 🏗️ Architecture
- **Modular Design**: Clean separation between scraping, parsing, and encoding
- **Extensible**: Easy to add support for new timing systems (SwimTopia, HyTek, etc.)
- **Type-Safe**: Full type hints with dataclasses and enums
- **Testable**: Comprehensive unit tests for all components
- **SOLID Principles**: Professional OOP architecture following industry best practices

### 🔌 Supported Systems
- ✅ **Microplus Timing** (fin*.microplustiming.com)
- 🔄 **Extensible framework** for additional systems

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Slthy/Microplus-Lenex
cd Microplus-Lenex

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Run the interactive CLI
python main.py
```

The CLI will guide you through three modes:
1. **Scrape and Process** — Complete workflow from URL to LENEX file
2. **Process Existing Data** — Convert already-scraped data
3. **Scrape Only** — Download data without processing

### Example

```
Competition URL: https://fin2022.microplustiming.com/NU_2022_07_28-08_04_Roma_web.php

✓ Scraping complete!
✓ Parsed: Campionati Italiani Assoluti Roma 2022
  - 4 sessions
  - 856 athletes  
  - 142 clubs
✓ Encoding complete!
✓ LENEX file saved: processed_data/Campionati_Italiani_Assoluti_Roma_2022.lef
```

---

## 📖 Programmatic Usage

### Simple Workflow

```python
from adapters import MicroplusAdapter
from encoders import LenexEncoder
from main import CompetitionProcessor

# Initialize
adapter = MicroplusAdapter()
encoder = LenexEncoder()
processor = CompetitionProcessor(adapter, encoder)

# Process competition
url = "https://fin2022.microplustiming.com/NU_2022_07_28-08_04_Roma_web.php"
processor.process_full_workflow(url)
```

### Step-by-Step Processing

```python
# Scrape data
processor.scrape(url)

# Parse into domain models
competition = processor.parse()

# Inspect data
print(f"Competition: {competition.name}")
print(f"Athletes: {len(competition.athletes)}")
print(f"Sessions: {len(competition.sessions)}")

# Encode to LENEX
lenex_xml = processor.encode()

# Save
processor.save(lenex_xml, "my_competition")
```

### Working with Domain Models

```python
from models import Competition, Athlete, Team, Gender, Course
from datetime import date

# Create competition manually
competition = Competition(
    name="My Swimming Meet",
    city="Rome",
    nation="ITA",
    course=Course.LONG_COURSE
)

# Add team
team = Team(name="Swim Club", code="SC", nation="ITA")
competition.clubs[team.code] = team

# Add athlete
athlete = Athlete(
    athlete_id="A001",
    firstname="John",
    lastname="Doe",
    gender=Gender.MALE,
    birthdate=date(2005, 1, 1),
    team=team
)
competition.add_athlete(athlete)

# Encode to LENEX
encoder = LenexEncoder()
xml = encoder.encode(competition)
```

---

## 🏗️ Architecture Overview

### Design Pattern: Strategy + Builder

```
┌─────────────────────────────────────────────────────┐
│                 Main Application                    │
│              (CompetitionProcessor)                 │
└───────────────┬─────────────────┬───────────────────┘
                │                 │
    ┌───────────▼──────────┐  ┌──-▼───────────────┐
    │   Data Adapter       │  │   Encoder         │
    │   (Strategy)         │  │   (Strategy)      │
    └───────────┬──────────┘  └──┬────────────────┘
                │                │
    ┌───────────▼──────────┐  ┌──▼────────────────┐
    │  MicroplusAdapter    │  │  LenexEncoder     │
    │  SwimTopiaAdapter    │  │  CSVEncoder       │
    │  HyTekAdapter        │  │  JSONEncoder      │
    └──────────────────────┘  └───────────────────┘
```

### Project Structure

```
src/
├── models.py          # Domain models (Competition, Athlete, Event, etc.)
├── adapters.py        # Data source adapters (Microplus, etc.)
├── encoders.py        # Output format encoders (LENEX, etc.)
├── utils.py           # Utility classes (TimeUtils, FinaPoints)
└── main.py           # Application entry point

tests/
├── test_models.py     # Model tests
├── test_adapters.py   # Adapter tests
├── test_encoders.py   # Encoder tests
└── test_utils.py      # Utility tests

data/
├── scraped_data/      # Raw JSON files (gitignored)
└── processed_data/    # Output LENEX files (gitignored)
```

---

## 🔧 Advanced Features

### Adding New Timing Systems

Easily extend support to other timing systems:

```python
from adapters import DataAdapter
from models import Competition

class SwimTopiaAdapter(DataAdapter):
    """Adapter for SwimTopia timing system."""
    
    def validate_source(self, source: str) -> bool:
        return "swimtopia.com" in source
    
    def scrape_data(self, source: str) -> None:
        # SwimTopia-specific scraping logic
        pass
    
    def parse_competition(self) -> Competition:
        # Parse SwimTopia data into Competition object
        return competition

# Use it immediately
adapter = SwimTopiaAdapter()
processor = CompetitionProcessor(adapter, encoder)
processor.process_full_workflow(swimtopia_url)
```

### Adding New Output Formats

Support additional export formats:

```python
from encoders import Encoder

class CSVEncoder(Encoder):
    """Export competition data to CSV."""
    
    def encode(self, competition: Competition) -> str:
        # Generate CSV from competition data
        return csv_data
    
    def save(self, data: str, filename: str) -> None:
        # Save CSV file
        pass

# Use multiple encoders
lenex_encoder = LenexEncoder()
csv_encoder = CSVEncoder()

processor = CompetitionProcessor(adapter, lenex_encoder)
lenex_xml = processor.encode()

# Also export to CSV
csv_data = csv_encoder.encode(processor.competition)
csv_encoder.save(csv_data, "results")
```

### Batch Processing

Process multiple competitions:

```python
urls = [
    "https://fin2022.microplustiming.com/NU_2022_07_28_Roma_web.php",
    "https://fin2023.microplustiming.com/NU_2023_08_01_Milano_web.php",
]

for url in urls:
    processor = CompetitionProcessor(adapter, encoder)
    processor.process_full_workflow(url)
```

---

## 📊 Data Analysis

Extract insights from competition data:

```python
# Parse competition
competition = processor.parse()

# Find fastest 100m freestyle time
from utils import TimeUtils

fastest = float('inf')
for athlete_id, results in competition.athlete_results.items():
    for result in results:
        if result.swimtime != 'NT':
            time = TimeUtils.time_to_timedelta(result.swimtime).total_seconds()
            if time < fastest:
                fastest = time
                fastest_athlete = competition.athletes[athlete_id]

print(f"Fastest: {fastest_athlete.firstname} {fastest_athlete.lastname}")
print(f"Time: {fastest:.2f}s")

# Count events by stroke
from collections import Counter
strokes = Counter()
for session in competition.sessions:
    for event in session.events:
        strokes[event.swimstyle.stroke] += 1

print(f"\nEvents by stroke: {strokes}")
```

---

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_models.py -v
```

---

## 📋 Requirements

- **Python**: 3.9 or higher
- **Dependencies**:
  - `requests` — HTTP library for web scraping
  - `inquirer` — Interactive CLI prompts
  - `python-dateutil` — Date parsing utilities

### Development Dependencies

```bash
pip install -r requirements-dev.txt
```

Includes: `pytest`, `mypy`, `black`, `pylint`

---

## 🎓 LENEX Format

**LENEX** (Lenex Exchange Format) is the international standard for swimming competition data. This encoder produces **LENEX 3.0** compliant XML files that can be imported into:

- SwimRankings.net
- Splash Meet Manager
- Team Manager
- Hy-Tek Meet Manager
- Swiss Timing
- Other swimming management software

### Output Features
✅ Complete competition metadata (name, location, dates)  
✅ Session and event structure  
✅ Athlete entries with qualifying times  
✅ Race results with placements  
✅ Split times (50m, 100m, 200m, etc.)  
✅ Relay team composition  
✅ FINA/World Aquatics points (2023 tables)  
✅ Age group classifications  
✅ Club/team information  

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Adding a New Timing System

1. Create a new adapter in `src/adapters.py`
2. Implement the `DataAdapter` interface
3. Add tests in `tests/test_adapters.py`
4. Submit a pull request

### Reporting Issues

Found a bug or have a suggestion? Please [open an issue](https://github.com/Slthy/Microplus-Lenex/issues) with:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Sample data (if applicable)

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE.md](LICENSE.md) file for details.

---

## 🙏 Acknowledgments

- **[LENEX 3.0 Technical Documentation][lenex_docs]** — International swimming data standard
- **Microplus Informatica Srl** — Timing system data structure
- **World Aquatics (FINA)** — 2023 point scoring tables

---

## 👨‍💻 Authors

**Original Code & Architecture**  
Alessandro Borsato — [@aborsato_][tw_link] on Twitter

**Version 2.0 Refactoring**  
Complete OOP redesign with extensible architecture

---

## 📞 Support

- 📧 **Issues**: [GitHub Issues](https://github.com/Slthy/Microplus-Lenex/issues)
- 📖 **Documentation**: See `/docs` folder for detailed guides
- 💬 **Discussions**: [GitHub Discussions](https://github.com/Slthy/Microplus-Lenex/discussions)

---

## 🗺️ Roadmap

### Version 2.1 (Planned)
- [ ] GUI interface with drag-and-drop
- [ ] Support for HyTek timing system
- [ ] Export to CSV and JSON formats
- [ ] Real-time competition monitoring
- [ ] Docker containerization

### Version 3.0 (Future)
- [ ] Web application with REST API
- [ ] Database storage for historical data
- [ ] Statistical analysis dashboard
- [ ] Multi-language support

---

## 📈 Changelog

### Version 2.0.0 (Current)
- ✨ Complete architectural refactoring
- ✨ OOP design with SOLID principles
- ✨ Extensible adapter system
- ✨ Type-safe domain models
- ✨ Comprehensive test suite
- ✨ FINA 2023 point tables
- ✨ Improved error handling
- ✨ Better documentation

### Version 1.0.0 (Legacy)
- Basic Microplus scraping
- LENEX 3.0 encoding
- Command-line interface

---

<div align="center">

**[⬆ Back to Top](#-lenexencoder-swimming-competition-data-processor)**

Made with ❤️ for the swimming community

</div>

[tw_link]: https://twitter.com/aborsato_
[lenex_docs]: https://wiki.swimrankings.net/images/6/62/Lenex_3.0_Technical_Documentation.pdf
