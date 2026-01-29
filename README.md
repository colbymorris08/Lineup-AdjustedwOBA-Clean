# Lineup Protection Projection Tool ⚾

**A baseball analytics tool that isolates true hitter talent by controlling for lineup protection and other context factors.**

---

## Executive Summary

Traditional batting metrics like wOBA and wRC+ tell us *what happened*, but not *why*. A hitter's performance is influenced by factors beyond their control: who bats behind them, what ballpark they play in, which pitchers they face, and where those pitchers locate their pitches.

This tool quantifies these context effects and strips them away, revealing **"True Talent"** — what each hitter would produce in a neutral environment.

### Key Finding: Lineup Protection Matters

When Aaron Judge bats behind you, pitchers can't pitch around you. They have to attack, giving you better pitches. This tool measures that advantage:

| Player | Protection Score | Protection Boost | Observed wOBA | Adjusted wOBA |
|--------|------------------|------------------|---------------|---------------|
| Juan Soto | .471 (Judge behind) | +.021 | .421 | .400 |
| Aaron Judge | .298 (weak protection) | -.005 | .476 | .481 |

**Soto benefits from +.021 wOBA due to protection. Judge produces elite numbers *despite* poor protection.**

---

## Features

### 🎚️ Layer Toggle System
Isolate individual effects or combine them:
- **Lineup Protection**: Adjust for on-deck hitter quality
- **Park Factors**: Adjust for ballpark effects (Coors vs. T-Mobile)
- **Pitcher Quality**: Adjust for opposing pitcher strength
- **Pitch Location**: Adjust for pitch location quality

### 📊 Interactive Leaderboards
- True Talent rankings (all layers)
- Protection Effect Only (isolate lineup impact)
- Park Effect Only (isolate ballpark impact)
- Biggest Risers/Fallers (who's over/underrated)

### 👤 Player Deep Dives
- Waterfall charts showing each adjustment
- Layer-by-layer breakdown with raw values
- Side-by-side observed vs. adjusted stats

### 📈 Visualizations
- Observed vs. Adjusted scatter plots
- Protection Score correlation analysis
- Team-level context effects
- Layer impact comparisons

---

## Methodology

### The Core Equation

```
Observed wOBA = True Talent + Protection Effect + Park Effect + Pitcher Effect + Location Effect
```

By estimating each context effect, we solve for True Talent.

### Layer 1: Lineup Protection

**Theory**: Hitters with dangerous batters behind them see better pitches because pitchers can't afford to pitch around them.

**Calculation**:
1. For each plate appearance, identify the on-deck hitter
2. Look up the on-deck hitter's season wOBA
3. Average across all PA to get "Protection Score"
4. Compare to league average (.331)
5. Apply coefficient: +0.1 protection diff ≈ +0.015 wOBA boost

**Example**:
```
Soto's Protection Score: .471 (Judge on deck)
League Average: .331
Difference: +.140
wOBA Boost: .140 × 0.15 = +.021
```

### Layer 2: Park Factors

**Theory**: Coors Field (113 PF) inflates stats ~13%; T-Mobile Park (94 PF) suppresses stats ~6%.

**Calculation**:
```python
park_adjusted_wOBA = observed_wOBA × (100 / park_factor)
```

### Layer 3: Pitcher Quality Faced

**Theory**: Schedule and lineup position affect which pitchers you face.

**Calculation**:
```python
avg_opp_FIP_minus = mean(opposing_pitcher_FIP_minus for all PA)
adjustment = (100 - avg_opp_FIP_minus) × 0.001
```

### Layer 4: Pitch Location Quality

**Theory**: Protected hitters see more pitches in the heart of the zone.

**Calculation**:
```python
heart_pct = pitches_in_heart_zone / total_pitches
adjustment = (heart_pct - league_avg) × 0.15
```

---

## Key Results (2024 Season)

### Most Overrated (Context-Boosted)
| Player | Team | Observed wOBA | True Talent wOBA | Total Boost |
|--------|------|---------------|------------------|-------------|
| Ryan McMahon | COL | .315 | .279 | +.038 |
| Brendan Rodgers | COL | .314 | .282 | +.037 |
| Brenton Doyle | COL | .328 | .296 | +.035 |

*Rockies hitters benefit most from Coors Field.*

### Most Underrated (Context-Suppressed)
| Player | Team | Observed wOBA | True Talent wOBA | Total Penalty |
|--------|------|---------------|------------------|---------------|
| Julio Rodríguez | SEA | .321 | .345 | -.026 |
| Cal Raleigh | SEA | .323 | .346 | -.025 |
| Shea Langeliers | OAK | .315 | .334 | -.019 |

*Mariners/A's hitters suppressed by pitcher-friendly parks.*

### Best Protected Hitters
| Player | Protection Score | On-Deck Hitter |
|--------|------------------|----------------|
| Juan Soto | .471 | Aaron Judge |
| Maikel Garcia | .409 | Bobby Witt Jr. |
| Mookie Betts | .405 | Shohei Ohtani/Freddie Freeman |

### Worst Protected Hitters
| Player | Protection Score | Context |
|--------|------------------|---------|
| Salvador Perez | .272 | Weak KC lineup behind him |
| Rafael Devers | .286 | Post-Bogaerts Boston |
| Aaron Judge | .298 | No elite hitter behind |

---

## Installation

### Requirements
- Python 3.9+
- ~500MB disk space (includes Statcast data)

### Setup

```bash
# 1. Unzip the package
unzip lineup_protection_tool.zip -d lineup_protection
cd lineup_protection

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`

---

## File Structure

```
lineup_protection/
├── app.py                      # Streamlit dashboard (main entry point)
├── data_processor.py           # Core calculation engine
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── statcast_2024_full.csv      # 713,703 pitches (Statcast)
├── fangraphs_batting.csv       # 129 qualified batters
├── fangraphs_pitching.csv      # 58 qualified pitchers
├── fangraphs_park_factors.csv  # 30 team park factors
├── fangraphs_woba_constants.csv # wOBA linear weights
│
├── season_protection_summary.csv  # Protection scores by player
└── game_protection_scores.csv     # PA-level protection data
```

---

## Data Sources

| Source | Description | Records |
|--------|-------------|---------|
| Baseball Savant | Pitch-by-pitch Statcast data | 713,703 pitches |
| FanGraphs | Qualified batter statistics | 129 players |
| FanGraphs | Qualified pitcher statistics | 58 pitchers |
| FanGraphs | 5-year park factors | 30 teams |
| FanGraphs | 2024 wOBA linear weights | 1 season |

---

## Usage Examples

### Isolate Lineup Protection Effect
1. Uncheck all layers except "Lineup Protection"
2. Go to Leaderboards → "Protection Effect Only"
3. See exactly how much each player benefits/suffers from protection

### Compare Two Players
1. Go to Player Analysis
2. Select Player A, note their adjustments
3. Select Player B, compare waterfall charts

### Find Undervalued Hitters
1. Check all layers
2. Go to Leaderboards → "Biggest Risers"
3. These players are suppressed by context — potential buy-low targets

---

## Limitations & Future Work

### Current Limitations
- **Single season**: 2024 only; multi-year analysis would be more stable
- **Qualified batters only**: 129 players with 300+ PA
- **Coefficient estimation**: Adjustment coefficients are theoretical; could be calibrated empirically
- **No platoon splits**: L/R matchups not yet incorporated

### Future Enhancements
- Historical validation (do adjustments predict future performance?)
- Player-specific protection effects (some hitters may benefit more)
- In-game leverage adjustments
- Trade value implications

---

## Technical Notes

### Protection Score Calculation
Protection scores are calculated from Statcast pitch-level data by:
1. Grouping pitches into plate appearances
2. Ordering PA by `game_pk`, `inning`, `at_bat_number`
3. Identifying the next batter in each half-inning
4. Looking up that batter's season wOBA
5. Averaging across all PA for each hitter

### Pitch Zone Classification
Heart zone defined as inner third of strike zone:
- X: -0.33 to 0.33 feet from center
- Z: sz_bot + 0.5 to sz_top - 0.5

---

## Author

MLB Analytics Interview Project  
January 2025

---

## License

For interview/portfolio use. Data sourced from public Baseball Savant and FanGraphs exports.
# LineupAdjustedwOBA
