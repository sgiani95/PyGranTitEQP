# prototype.py: Quick and dirty PyGranTitEQP prototype
# Loads data.dat (volume in mL, potential in mV) and plots titration curve, Gran G1, and Gran G2

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def load_data(file_path):
    """Load titration data from a text file."""
    try:
        # Assume space-separated, no headers
        # Adjust delimiter (e.g., delimiter=',') or header (e.g., header=0) if needed
        df = pd.read_csv(file_path, delim_whitespace=True, names=['volume', 'potential'])
        print("Data loaded successfully:")
        print(df.head())
        return df
    except FileNotFoundError:
        print(f"Error: '{file_path}' not found. Ensure the file is in the same directory.")
        return None
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def validate_data(df):
    """Validate titration data for monotonic volumes and reasonable potentials."""
    if df is None:
        print("No data to validate.")
        return False
    # Check monotonic increasing volumes
    if not df['volume'].is_monotonic_increasing:
        print("Warning: Volumes are not strictly increasing. Check data integrity.")
        return False
    # Check reasonable potential values (mV, -2000 to 2000)
    if (df['potential'] < -2000).any() or (df['potential'] > 2000).any():
        print("Warning: Potential values outside typical mV range (-2000 to 2000).")
    print(f"Data points: {len(df)}")
    return True

def plot_titration_and_gran(df, output_file='titration_and_gran.png'):
    """Plot titration curve, Gran G1, and Gran G2 in separate subplots."""
    if df is None or not validate_data(df):
        print("Cannot plot: Invalid or no data.")
        return
    # Set professional plot style
    plt.style.use('seaborn-v0_8')
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 12), sharex=True)

    # Plot 1: Titration curve (potential vs. volume)
    ax1.plot(df['volume'], df['potential'], marker='o', linestyle='-', color='blue', label='Titration Data')
    ax1.set_ylabel('Potential (mV)')
    ax1.set_title('Titration Curve')
    ax1.grid(True)
    ax1.legend()

    # Plot 2: Gran G1 = (v + V) * 10^E vs. volume
    V = 5.0  # Initial volume to be titrated (mL)
    gran_g1 = (df['volume'] + V) * np.power(10, df['potential'])
    ax2.plot(df['volume'], gran_g1, marker='o', linestyle='-', color='green', label='G1 = (v + V) * 10^E')
    ax2.set_ylabel('Gran G1')
    ax2.set_title('Gran G1 Plot')
    ax2.grid(True)
    ax2.legend()

    # Plot 3: Gran G2 = (v + V) * 10^(-E) vs. volume
    gran_g2 = (df['volume'] + V) * np.power(10, -df['potential'])
    ax3.plot(df['volume'], gran_g2, marker='s', linestyle='--', color='red', label='G2 = (v + V) * 10^(-E)')
    ax3.set_xlabel('Volume Added (mL)')
    ax3.set_ylabel('Gran G2')
    ax3.set_title('Gran G2 Plot')
    ax3.grid(True)
    ax3.legend()

    plt.tight_layout()
    # Save combined plot
    plt.savefig(output_file, dpi=300)
    print(f"Plots saved as '{output_file}'")
    plt.show()

def main():
    """Main function to run the prototype."""
    file_path = 'data.dat'
    df = load_data(file_path)
    if df is not None:
        plot_titration_and_gran(df)

if __name__ == '__main__':
    main()