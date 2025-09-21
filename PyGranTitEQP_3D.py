# second_prototype.py: Second Python script for PyGranTitEQP
# Loads data.dat (volume in mL, pH) and plots titration curve and G1's for different initial volumes V (1,5,10,...,50)

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

def plot_titration_and_g1_v_vary(df, output_file='titration_and_g1_v_vary.png'):
    """Plot titration curve and G1's for different initial volumes V in a 5x1 grid."""
    if df is None or not validate_data(df):
        print("Cannot plot: Invalid or no data.")
        return
    # Set professional plot style
    plt.style.use('seaborn')

    # Convert to NumPy arrays for plotting
    volume = df['volume'].to_numpy()
    pH = df['pH'].to_numpy()

    # V values
    V_values = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
    
    # Define G1 functions
    def strongacid_g1(volume, pH, V):
        return (volume + V) * np.power(10, -pH)

    def strongbase_g1(volume, pH, V):
        return (volume + V) * np.power(10, pH)

    def weakacid_g1(volume, pH, V):
        return volume * np.power(10, -pH)  # No V dependence

    def weakbase_g1(volume, pH, V):
        return volume * np.power(10, pH)  # No V dependence

    # G1 types and labels
    g1_types = [strongacid_g1, strongbase_g1, weakacid_g1, weakbase_g1]
    g1_labels = ['StrongAcid_G1', 'StrongBase_G1', 'WeakAcid_G1', 'WeakBase_G1']

    # Color map for V values
    colors = plt.cm.viridis(np.linspace(0, 1, len(V_values)))

    # Create figure with 5 rows, 1 column
    fig, axes = plt.subplots(5, 1, figsize=(8, 25), sharex=True)

    # Row 1: Titration curve
    axes[0].plot(volume, pH, marker='o', linestyle='-', color='blue', label='Titration Data')
    axes[0].set_ylabel('pH')
    axes[0].set_title('Titration Curve')
    axes[0].grid(True)
    axes[0].legend()

    # Rows 2-5: Each G1 type with multiple V lines
    for row in range(1, 5):
        g1_func = g1_types[row-1]
        label = g1_labels[row-1]
        axes[row].set_ylabel(label)
        axes[row].set_title(label + ' for different V')
        axes[row].grid(True)

        for i, V in enumerate(V_values):
            g1 = g1_func(volume, pH, V)
            axes[row].plot(volume, g1, label=f'V={V}', color=colors[i])
        
        # Only show legend for StrongAcid_G1 (row 2, index 1)
        if row == 1:
            axes[row].legend(ncol=3, bbox_to_anchor=(0.75, 1.0), loc='upper center', fontsize='small')
            
        #axes[row].legend(ncol=3, bbox_to_anchor=(0.5, -0.2), loc='upper center', fontsize='small')

    # Set x-axis label on the last row
    axes[-1].set_xlabel('Volume Added (mL)')

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
        plot_titration_and_g1_v_vary(df)

if __name__ == '__main__':
    main()