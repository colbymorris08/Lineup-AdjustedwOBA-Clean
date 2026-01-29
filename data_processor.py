"""
Lineup Protection Projection Tool - Data Processor
Calculates adjusted batting metrics controlling for context factors.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

class LineupProtectionProcessor:
    """Process and analyze lineup protection effects on batting performance."""
    
    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.statcast = None
        self.batting = None
        self.pitching = None
        self.park_factors = None
        self.woba_constants = None
        self.protection_scores = None
        
    def load_all_data(self) -> None:
        """Load all required datasets."""
        print("Loading datasets...")

        # Only load Statcast if not already provided
        if self.statcast is None:
            import glob
            statcast_files = sorted(glob.glob(f"{self.data_dir}/statcast_2024_part*.csv"))
            self.statcast = pd.concat([pd.read_csv(f, low_memory=False) for f in statcast_files], ignore_index=True)
        print(f"  Statcast: {len(self.statcast):,} pitches")

        # FanGraphs batting stats
        self.batting = pd.read_csv(f"{self.data_dir}/fangraphs_batting.csv")
        print(f"  Batting: {len(self.batting)} players")

        # FanGraphs pitching stats
        self.pitching = pd.read_csv(f"{self.data_dir}/fangraphs_pitching.csv")
        print(f"  Pitching: {len(self.pitching)} pitchers")

        # Park factors
        self.park_factors = pd.read_csv(f"{self.data_dir}/fangraphs_park_factors.csv")
        print(f"  Park factors: {len(self.park_factors)} teams")

        # wOBA constants
        self.woba_constants = pd.read_csv(f"{self.data_dir}/fangraphs_woba_constants.csv")
        print(f"  wOBA constants: {len(self.woba_constants)} seasons")

        # Lineup protection scores
        self.protection_scores = pd.read_csv(f"{self.data_dir}/season_protection_summary.csv")
        print(f"  Protection scores: {len(self.protection_scores)} players")

        print("✅ All data loaded")
        
    def get_2024_woba_weights(self) -> Dict[str, float]:
        """Get 2024 wOBA linear weights."""
        w2024 = self.woba_constants[self.woba_constants['Season'] == 2024].iloc[0]
        return {
            'wBB': w2024['wBB'],
            'wHBP': w2024['wHBP'],
            'w1B': w2024['w1B'],
            'w2B': w2024['w2B'],
            'w3B': w2024['w3B'],
            'wHR': w2024['wHR'],
            'wOBA_scale': w2024['wOBAScale'],
            'lg_wOBA': w2024['wOBA'],
            'R_PA': w2024['R/PA'],
            'R_W': w2024['R/W']
        }
    
    def classify_pitch_location(self, plate_x: float, plate_z: float, 
                                 sz_top: float = 3.5, sz_bot: float = 1.5) -> str:
        """Classify pitch location into zones."""
        zone_left, zone_right = -0.83, 0.83
        heart_left, heart_right = -0.33, 0.33
        heart_top, heart_bot = sz_top - 0.5, sz_bot + 0.5
        
        if (heart_left <= plate_x <= heart_right and 
            heart_bot <= plate_z <= heart_top):
            return 'heart'
        
        if (zone_left <= plate_x <= zone_right and 
            sz_bot <= plate_z <= sz_top):
            return 'zone'
        
        chase_buffer = 0.5
        if (zone_left - chase_buffer <= plate_x <= zone_right + chase_buffer and 
            sz_bot - chase_buffer <= plate_z <= sz_top + chase_buffer):
            return 'chase'
        
        return 'waste'
    
    def calculate_pitch_quality_by_batter(self) -> pd.DataFrame:
        """Calculate the quality of pitches seen by each batter."""
        df = self.statcast.copy()
        df = df.dropna(subset=['plate_x', 'plate_z'])
        
        df['sz_top'] = df['sz_top'].fillna(3.5)
        df['sz_bot'] = df['sz_bot'].fillna(1.5)
        
        df['pitch_zone'] = df.apply(
            lambda r: self.classify_pitch_location(r['plate_x'], r['plate_z'], r['sz_top'], r['sz_bot']),
            axis=1
        )
        
        # Aggregate by batter
        batter_pitch_quality = df.groupby('batter').agg({
            'pitch_zone': lambda x: (x == 'heart').mean(),
            'plate_x': 'count'
        }).rename(columns={
            'pitch_zone': 'heart_pct',
            'plate_x': 'total_pitches'
        })
        
        # Zone percentages
        zone_pcts = df.groupby('batter')['pitch_zone'].apply(
            lambda x: pd.Series({
                'zone_pct': ((x == 'heart') | (x == 'zone')).mean(),
                'chase_pct': (x == 'chase').mean(),
                'waste_pct': (x == 'waste').mean()
            })
        ).unstack()
        
        batter_pitch_quality = batter_pitch_quality.join(zone_pcts)
        return batter_pitch_quality.reset_index()
    
    def calculate_pitcher_quality_faced(self) -> pd.DataFrame:
        """Calculate average pitcher quality faced by each batter."""
        pitcher_quality = self.pitching[['MLBAMID', 'FIP', 'xFIP', 'ERA']].copy()
        pitcher_quality = pitcher_quality.rename(columns={'MLBAMID': 'pitcher'})
        
        lg_fip = self.pitching['FIP'].mean()
        pitcher_quality['FIP_minus'] = (pitcher_quality['FIP'] / lg_fip) * 100
        
        df = self.statcast[['batter', 'pitcher', 'game_pk']].drop_duplicates()
        df = df.merge(pitcher_quality, on='pitcher', how='left')
        df['FIP_minus'] = df['FIP_minus'].fillna(100)
        df['FIP'] = df['FIP'].fillna(lg_fip)
        
        batter_opp = df.groupby('batter').agg({
            'FIP_minus': 'mean',
            'FIP': 'mean',
            'pitcher': 'nunique'
        }).rename(columns={
            'FIP_minus': 'avg_pitcher_fip_minus',
            'FIP': 'avg_pitcher_fip',
            'pitcher': 'unique_pitchers_faced'
        })
        
        return batter_opp.reset_index()
    
    def merge_protection_scores(self) -> pd.DataFrame:
        """Merge lineup protection scores with batting stats."""
        prot = self.protection_scores.copy()
        batting = self.batting.copy()
        
        # Merge on MLBAMID
        merged = batting.merge(
            prot[['batter_id', 'avg_protection_score', 'games', 'total_pa', 'avg_batting_order']],
            left_on='MLBAMID',
            right_on='batter_id',
            how='left'
        )
        
        return merged
    
    def calculate_park_adjusted_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply park factor adjustments to batting stats."""
        pf = self.park_factors[['Team', 'Basic (5yr)']].copy()
        pf.columns = ['Team', 'park_factor']
        
        # Handle team name mapping (FanGraphs uses abbreviations)
        team_map = {
            'Angels': 'LAA', 'Astros': 'HOU', 'Athletics': 'OAK', 'Blue Jays': 'TOR',
            'Braves': 'ATL', 'Brewers': 'MIL', 'Cardinals': 'STL', 'Cubs': 'CHC',
            'Diamondbacks': 'ARI', 'Dodgers': 'LAD', 'Giants': 'SFG', 'Guardians': 'CLE',
            'Mariners': 'SEA', 'Marlins': 'MIA', 'Mets': 'NYM', 'Nationals': 'WSN',
            'Orioles': 'BAL', 'Padres': 'SDP', 'Phillies': 'PHI', 'Pirates': 'PIT',
            'Rangers': 'TEX', 'Rays': 'TBR', 'Red Sox': 'BOS', 'Reds': 'CIN',
            'Rockies': 'COL', 'Royals': 'KCR', 'Tigers': 'DET', 'Twins': 'MIN',
            'White Sox': 'CHW', 'Yankees': 'NYY'
        }
        pf['Team_Abbr'] = pf['Team'].map(team_map)
        
        df = df.merge(pf[['Team_Abbr', 'park_factor']], left_on='Team', right_on='Team_Abbr', how='left')
        df['park_factor'] = df['park_factor'].fillna(100)
        df['wOBA_park_adj'] = df['wOBA'] * (100 / df['park_factor'])
        
        return df
    
    def build_full_dataset(self) -> pd.DataFrame:
        """Build the complete dataset with all adjustments."""
        print("\n🔧 Building full dataset with all adjustments...")
        
        print("  Merging protection scores...")
        df = self.merge_protection_scores()
        
        print("  Applying park factors...")
        df = self.calculate_park_adjusted_stats(df)
        
        print("  Calculating pitch quality faced...")
        pitch_quality = self.calculate_pitch_quality_by_batter()
        df = df.merge(pitch_quality, left_on='MLBAMID', right_on='batter', how='left')
        
        print("  Calculating pitcher quality faced...")
        pitcher_opp = self.calculate_pitcher_quality_faced()
        df = df.merge(pitcher_opp, left_on='MLBAMID', right_on='batter', how='left', suffixes=('', '_drop'))
        df = df.drop(columns=[c for c in df.columns if c.endswith('_drop')])
        
        print("  Calculating True Talent projections...")
        df = self.calculate_true_talent(df)
        
        print(f"✅ Full dataset built: {len(df)} players, {len(df.columns)} columns")
        return df
    
    def calculate_true_talent(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate True Talent wOBA by adjusting for context factors."""
        lg_woba = df['wOBA'].mean()
        lg_protection = df['avg_protection_score'].mean()
        lg_fip_minus = 100
        lg_heart_pct = df['heart_pct'].mean() if 'heart_pct' in df.columns else 0.15
        
        # Protection adjustment: higher protection = boost to observed wOBA
        # Coefficient: +0.1 protection score difference = ~0.015 wOBA difference
        protection_coef = 0.15
        df['protection_adj'] = (df['avg_protection_score'].fillna(lg_protection) - lg_protection) * protection_coef
        
        # Park adjustment
        df['park_adj'] = df['wOBA'] - df['wOBA_park_adj']
        
        # Pitcher quality adjustment
        # Facing lower FIP- = tougher pitching = suppresses wOBA
        pitcher_coef = 0.001
        df['pitcher_adj'] = (100 - df['avg_pitcher_fip_minus'].fillna(100)) * pitcher_coef
        
        # Pitch quality adjustment
        # More heart pitches = easier context
        heart_coef = 0.15
        df['pitch_quality_adj'] = (df['heart_pct'].fillna(lg_heart_pct) - lg_heart_pct) * heart_coef
        
        # True Talent wOBA: remove favorable context boosts
        df['wOBA_true_talent'] = (df['wOBA'] 
                                   - df['protection_adj'] 
                                   - df['park_adj'] 
                                   + df['pitcher_adj']  # Add back if faced tough pitching
                                   - df['pitch_quality_adj'])
        
        # Regress slightly to mean for stability
        regression_factor = 0.10
        df['wOBA_true_talent'] = (df['wOBA_true_talent'] * (1 - regression_factor) + 
                                   lg_woba * regression_factor)
        
        # Calculate wRC+ style metric
        weights = self.get_2024_woba_weights()
        lg_rppa = weights['R_PA']
        
        # True Talent wRC+
        df['wRAA_true_talent'] = ((df['wOBA_true_talent'] - lg_woba) / weights['wOBA_scale'] * df['PA'])
        df['wRC_plus_true_talent'] = (((df['wRAA_true_talent'] / df['PA'] + lg_rppa) / lg_rppa) * 100)
        
        # Total context adjustment
        df['total_context_adj'] = df['protection_adj'] + df['park_adj'] - df['pitcher_adj'] + df['pitch_quality_adj']
        
        return df


if __name__ == "__main__":
    processor = LineupProtectionProcessor(".")
    processor.load_all_data()
    
    df = processor.build_full_dataset()
    
    print("\nTop 10 by True Talent wOBA:")
    print(df.nlargest(10, 'wOBA_true_talent')[['Name', 'Team', 'wOBA', 'wOBA_true_talent', 'total_context_adj']].to_string(index=False))
    
    print("\n\nBiggest positive context boost (overrated):")
    print(df.nlargest(10, 'total_context_adj')[['Name', 'Team', 'wOBA', 'wOBA_true_talent', 'total_context_adj']].to_string(index=False))
    
    print("\n\nBiggest negative context (underrated):")
    print(df.nsmallest(10, 'total_context_adj')[['Name', 'Team', 'wOBA', 'wOBA_true_talent', 'total_context_adj']].to_string(index=False))
