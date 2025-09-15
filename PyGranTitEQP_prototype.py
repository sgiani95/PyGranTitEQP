# prototype.py: Quick and dirty PyGranTitEQP prototype
# Loads data.dat (volume in mL, pH) and plots titration curve and Gran plots (G1.1, G1.2, G1.3, G2.1, G2.2, G2.3) in a 4x2 grid

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def load_data(file_path):
    """Load titration data from a text file."""
    try:
        # Assume space-separated, no headers
        # Adjust delimiter (e.g., delimiter=',') or header (e.g., header=0) if needed
        df = pd.read_csv(file_path, delim_whitespace=True, names=['volume', 'pH'])
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
    """Validate titration data for monotonic volumes and reasonable pH."""
    if df is None:
        print("No data to validate.")
        return False
    # Check monotonic increasing volumes
    if not df['volume'].is_monotonic_increasing:
        print("Warning: Volumes are not strictly increasing. Check data integrity.")
        return False
    # Check reasonable pH values (0 to 14)
    if (df['pH'] < 0).any() or (df['pH'] > 14).any():
        print("Warning: pH values outside typical range (0 to 14).")
    print(f"Data points: {len(df)}")
    return True

def plot_titration_and_gran(df, output_file='titration_and_gran.png'):
    """Plot titration curve and Gran plots (G1.1, G1.2, G1.3, G2.1, G2.2, G2.3) in a 4x2 grid."""
    if df is None or not validate_data(df):
        print("Cannot plot: Invalid or no data.")
        return
    # Set professional plot style
    plt.style.use('seaborn')
    fig, axes = plt.subplots(4, 2, figsize=(12, 16), sharex=True)

    # Convert to NumPy arrays for plotting
    volume = df['volume'].to_numpy()
    pH = df['pH'].to_numpy()
    V = 25.0  # Initial volume to be titrated (mL)

    # Row 1: Titration curve in both columns
    axes[0, 0].plot(volume, pH, marker='o', linestyle='-', color='blue', label='Titration Data')
    axes[0, 0].set_ylabel('pH')
    axes[0, 0].set_title('Titration Curve')
    axes[0, 0].grid(True)
    axes[0, 0].legend()

    axes[0, 1].plot(volume, pH, marker='o', linestyle='-', color='blue', label='Titration Data')
    axes[0, 1].set_ylabel('pH')
    axes[0, 1].set_title('Titration Curve')
    axes[0, 1].grid(True)
    axes[0, 1].legend()

    # Row 2: G1.1 (left), G2.1 (right)
    g1_1 = (volume + V) * np.power(10, -pH)  # G1.1 = (v + V) * 10^(-pH)
    g2_1 = (volume + V) * np.power(10,  pH)  # G2.1 = (v + V) * 10^(pH)
    axes[1, 0].plot(volume, g1_1, marker='o', linestyle='-', color='green', label='G1.1 = (v + V) * 10^(-pH)')
    axes[1, 0].set_ylabel('Gran G1.1')
    axes[1, 0].set_title('Gran G1.1 Plot')
    axes[1, 0].grid(True)
    axes[1, 0].legend()
    # Optional: Uncomment for log-scaling if values are too large/small
    # axes[1, 0].set_yscale('log')

    axes[1, 1].plot(volume, g2_1, marker='o', linestyle='-', color='red', label='G2.1 = (v + V) * 10^(pH)')
    axes[1, 1].set_ylabel('Gran G2.1')
    axes[1, 1].set_title('Gran G2.1 Plot')
    axes[1, 1].grid(True)
    axes[1, 1].legend()
    # axes[1, 1].set_yscale('log')

    # Row 3: G1.2 (left), G2.2 (right)
    g1_2 = (volume    ) * np.power(10, -pH)  # G1.2 = v * 10^(-pH)
    g2_2 = (volume + V) * np.power(10,  pH)  # G2.2 = (v + V) * 10^(pH)
    axes[2, 0].plot(volume, g1_2, marker='s', linestyle='--', color='orange', label='G1.2 = v * 10^(-pH)')
    axes[2, 0].set_ylabel('Gran G1.2')
    axes[2, 0].set_title('Gran G1.2 Plot')
    axes[2, 0].grid(True)
    axes[2, 0].legend()
    # axes[2, 0].set_yscale('log')

    axes[2, 1].plot(volume, g2_2, marker='s', linestyle='--', color='cyan', label='G2.2 = (v + V) * 10^(pH)')
    axes[2, 1].set_ylabel('Gran G2.2')
    axes[2, 1].set_title('Gran G2.2 Plot')
    axes[2, 1].grid(True)
    axes[2, 1].legend()
    # axes[2, 1].set_yscale('log')

    # Row 4: G1.3 (left), G2.3 (right)
    g1_3 = (volume    ) * np.power(10,  pH)  # G1.3 = v * 10^(pH)
    g2_3 = (volume + V) * np.power(10, -pH)  # G2.3 = (v + V) * 10^(-pH)
    axes[3, 0].plot(volume, g1_3, marker='^', linestyle=':', color='purple', label='G1.3 = v * 10^(pH)')
    axes[3, 0].set_xlabel('Volume Added (mL)')
    axes[3, 0].set_ylabel('Gran G1.3')
    axes[3, 0].set_title('Gran G1.3 Plot')
    axes[3, 0].grid(True)
    axes[3, 0].legend()
    # axes[3, 0].set_yscale('log')

    axes[3, 1].plot(volume, g2_3, marker='^', linestyle=':', color='magenta', label='G2.3 = (v + V) * 10^(-pH)')
    axes[3, 1].set_xlabel('Volume Added (mL)')
    axes[3, 1].set_ylabel('Gran G2.3')
    axes[3, 1].set_title('Gran G2.3 Plot')
    axes[3, 1].grid(True)
    axes[3, 1].legend()
    # axes[3, 1].set_yscale('log')

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