#!/usr/bin/env python3
"""Plot Corrupted Gauntlet DPS over time to track improvement."""

import json
import glob
import re
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt

# Minimum ticks to count as a real run (filters out immediate leaves)
MIN_TICKS = 100

def get_runelite_data_dir():
    """Find the RuneLite gauntlet tracker data directory."""
    home = Path.home()

    # Try common locations
    possible_paths = [
        home / ".runelite" / "gauntletPerformanceTracker" / "data",  # Linux/Mac
        home / "AppData" / "Local" / "RuneLite" / "gauntletPerformanceTracker" / "data",  # Windows
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None

def get_available_users(data_dir):
    """List available usernames (subdirectories in data dir)."""
    if not data_dir:
        return []
    return [d.name for d in data_dir.iterdir() if d.is_dir()]

def select_user(users):
    """Prompt user to select from available usernames."""
    if len(users) == 1:
        print(f"Found user: {users[0]}")
        return users[0]

    print("Available users:")
    for i, user in enumerate(users, 1):
        print(f"  {i}. {user}")

    while True:
        try:
            choice = input("Select user (number): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(users):
                return users[idx]
        except (ValueError, IndexError):
            pass
        print("Invalid choice, try again.")

def parse_filename_date(filename):
    """Extract datetime from filename like gauntletTracker-dejagersh2-2025-11-26-19-42.json"""
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})\.json$', filename)
    if match:
        year, month, day, hour, minute = map(int, match.groups())
        return datetime(year, month, day, hour, minute)
    return None

def load_runs(data_dir, username):
    """Load all gauntlet runs and return sorted by date."""
    runs = []
    user_dir = data_dir / username
    pattern = str(user_dir / f"gauntletTracker-{username}-*.json")

    for filepath in glob.glob(pattern):
        date = parse_filename_date(filepath)
        if not date:
            continue

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if data.get('totalTicks', 0) < MIN_TICKS:
                    continue
                runs.append({
                    'date': date,
                    'dps_given': data.get('dpsGiven', 0),
                    'dps_taken': data.get('dpsTaken', 0),
                    'used_ticks': float(data.get('usedTicks', '0%').rstrip('%')),
                    'wrong_off_prayer': data.get('wrongOffensivePrayer', 0),
                    'wrong_def_prayer': data.get('wrongDefensivePrayer', 0),
                    'wrong_attack_style': data.get('wrongAttackStyle', 0),
                    'tornado_hits': data.get('tornadoHits', 0),
                    'total_ticks': data.get('totalTicks', 0),
                })
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading {filepath}: {e}")

    runs.sort(key=lambda x: x['date'])
    return runs

def moving_average(data, window=5):
    """Calculate moving average for a data series."""
    result = []
    for i in range(len(data)):
        start = max(0, i - window + 1)
        result.append(sum(data[start:i+1]) / (i - start + 1))
    return result

def plot_metric(ax, run_numbers, values, color, title, ylabel, invert=False):
    """Plot a single metric with moving average."""
    ax.scatter(run_numbers, values, alpha=0.6, color=color, s=20)
    ax.plot(run_numbers, values, alpha=0.3, color=color, linewidth=1)

    if len(values) >= 5:
        ma = moving_average(values)
        ax.plot(run_numbers, ma, color='red', linewidth=2, label='5-run avg')
        ax.legend(loc='upper right', fontsize=8)

    ax.set_xlabel('Run #')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    if invert:
        ax.invert_yaxis()

def plot_all_metrics(runs):
    """Plot all metrics in a multi-panel figure."""
    run_numbers = list(range(1, len(runs) + 1))
    dps_given = [r['dps_given'] for r in runs]
    dps_taken = [r['dps_taken'] for r in runs]
    used_ticks = [r['used_ticks'] for r in runs]
    wrong_off = [r['wrong_off_prayer'] for r in runs]
    wrong_def = [r['wrong_def_prayer'] for r in runs]
    wrong_style = [r['wrong_attack_style'] for r in runs]
    tornado_hits = [r['tornado_hits'] for r in runs]
    total_ticks = [r['total_ticks'] for r in runs]

    fig, axes = plt.subplots(4, 2, figsize=(14, 12))
    fig.suptitle('Corrupted Gauntlet Performance Over Time', fontsize=14, fontweight='bold')

    # DPS Given (higher is better)
    plot_metric(axes[0, 0], run_numbers, dps_given, 'green', 'DPS Given', 'DPS')

    # DPS Taken (lower is better)
    plot_metric(axes[0, 1], run_numbers, dps_taken, 'red', 'DPS Taken (lower = better)', 'DPS', invert=True)

    # Used Ticks % (higher is better)
    plot_metric(axes[1, 0], run_numbers, used_ticks, 'blue', 'Tick Efficiency', '% Ticks Used')

    # Wrong Offensive Prayer (lower is better)
    plot_metric(axes[1, 1], run_numbers, wrong_off, 'orange', 'Wrong Offensive Prayers (lower = better)', 'Count', invert=True)

    # Wrong Defensive Prayer (lower is better)
    plot_metric(axes[2, 0], run_numbers, wrong_def, 'purple', 'Wrong Defensive Prayers (lower = better)', 'Count', invert=True)

    # Wrong Attack Style (lower is better)
    plot_metric(axes[2, 1], run_numbers, wrong_style, 'brown', 'Wrong Attack Style (lower = better)', 'Count', invert=True)

    # Tornado Hits (lower is better)
    plot_metric(axes[3, 0], run_numbers, tornado_hits, 'cyan', 'Tornado Hits (lower = better)', 'Count', invert=True)

    # Total Ticks / Fight Duration (lower is better)
    plot_metric(axes[3, 1], run_numbers, total_ticks, 'magenta', 'Fight Duration (lower = faster)', 'Ticks', invert=True)

    plt.tight_layout()
    plt.savefig('gauntlet_performance.png', dpi=150)
    plt.show()

    print(f"\nChart saved to gauntlet_performance.png")

if __name__ == '__main__':
    data_dir = get_runelite_data_dir()
    if not data_dir:
        print("Could not find RuneLite gauntlet tracker data directory.")
        print("Expected locations:")
        print("  Linux/Mac: ~/.runelite/gauntletPerformanceTracker/data/")
        print("  Windows: %LOCALAPPDATA%/RuneLite/gauntletPerformanceTracker/data/")
        exit(1)

    users = get_available_users(data_dir)
    if not users:
        print(f"No user data found in {data_dir}")
        exit(1)

    username = select_user(users)
    runs = load_runs(data_dir, username)

    if not runs:
        print(f"No gauntlet data files found for {username}!")
    else:
        print(f"Found {len(runs)} runs for {username}")
        plot_all_metrics(runs)
