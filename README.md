# Lineup Protection Projection Tool ⚾

**A baseball analytics tool that isolates true hitter talent by controlling for lineup protection and context factors.**

🔗 **[Live App](https://lineup-adjustedwoba-clean-colbymorris.streamlit.app/)**

---

## Overview

Traditional batting metrics like wOBA tell us *what happened*, but not *why*. A hitter's stats are influenced by context factors beyond their control. This tool quantifies those effects and removes them to reveal **True Talent**.

### The Core Innovation: Two-Way Lineup Protection

**Hitter Behind (On-Deck Protection)**
- When a dangerous hitter bats behind you, pitchers can't pitch around you
- They have to attack, giving you better pitches
- Example: Juan Soto with Aaron Judge behind him

**Hitter In Front (Preceding Protection)**
- When a good hitter bats in front of you, more runners are on base
- Pitchers work from the stretch, increasing mistakes
- More RBI opportunities in favorable counts

---

## Data Coverage

| Metric | Value |
|--------|-------|
| **Date Range** | March 28 - June 30, 2024 |
| **Pitches Analyzed** | ~350,000 |
| **Players** | 129 qualified batters |
| **Source** | Baseball Savant Statcast |

*Note: Uses first half of 2024 season data for faster load times.*

---

## Adjustment Layers

| Layer | Description |
|-------|-------------|
| **Lineup Protection** | On-deck + preceding hitter wOBA |
| **Park Factors** | FanGraphs 5-year park factors |
| **Pitcher Quality** | Average opponent FIP- faced |
| **Pitch Location** | Heart-zone pitch frequency |

---

## Key Findings

**Most Context-Boosted:**
- Rockies hitters benefit from Coors Field (+13% park factor)
- Hitters with elite teammates in lineup spots around them

**Most Context-Suppressed:**
- Mariners hitters hurt by T-Mobile Park (-6% park factor)
- Cleanup hitters with weak protection behind them

---

## Installation
```bash
git clone https://github.com/colbymorris08/Lineup-AdjustedwOBA-Clean.git
cd Lineup-AdjustedwOBA-Clean
pip install -r requirements.txt
streamlit run app.py
```

---

## Files

| File | Description |
|------|-------------|
| `app.py` | Streamlit dashboard |
| `data_processor.py` | Core calculation engine |
| `statcast_2024_part*.csv` | Pitch-by-pitch data (8 files) |
| `fangraphs_*.csv` | Batting, pitching, park factors |
| `season_protection_summary.csv` | Pre-calculated protection scores |

---

## Methodology

### Protection Score Calculation

For each plate appearance:
1. Identify the on-deck hitter (batting behind)
2. Identify the preceding hitter (batting in front)
3. Look up each hitter's season wOBA
4. Average across all PA for each batter
5. Compare to league average
6. Convert difference to wOBA adjustment
```python
protection_adj = (player_protection - league_avg) * coefficient
```

### True Talent Formula
```
True Talent wOBA = Observed wOBA
                   - Protection Adjustment (behind + in front)
                   - Park Adjustment
                   + Pitcher Quality Adjustment
                   - Pitch Location Adjustment
```

---

## Author

Colby Morris — MLB Analytics Project, January 2025

## Data Sources

- [Baseball Savant](https://baseballsavant.mlb.com) (Statcast)
- [FanGraphs](https://fangraphs.com) (batting, pitching, park factors)
