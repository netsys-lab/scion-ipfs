import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

MASTER_FILE = 'master_results.csv'
OUTPUT_FILE = 'plot_single_comparison_final.png'
OUTPUT_FILE2 = 'plot_single_comparison_final.pdf'

# --- Define constants for the specific plot ---
TARGET_DEPLOYMENT = 'random'
TARGET_N_NODES = 10000

def main():
    """
    Generates a single plot to compare strategies for N=10000,
    with a fully descriptive, unified legend.
    """
    try:
        df = pd.read_csv(MASTER_FILE)
    except FileNotFoundError:
        print(f"Error: '{MASTER_FILE}' not found. Please check your source file.")
        return

    # --- Set the font to a built-in serif font ---
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman', 'Garamond', 'DejaVu Serif']
    plt.rcParams['pdf.fonttype'] = 42

    # --- Step 1: Filter data for the specific scenario ---
    df_plot = df[(df['scion_deployment'] == TARGET_DEPLOYMENT) &
                 (df['num_nodes'] == TARGET_N_NODES)].copy()

    if df_plot.empty:
        print(f"Error: No data found for N={TARGET_N_NODES} and deployment='{TARGET_DEPLOYMENT}'.")
        print("Please check your master_results.csv file.")
        return

    # --- Step 2: Prepare data and legend labels ---

    # A. Data for the 'default' strategy.
    df_default = df_plot[df_plot['kademlia_strategy'] == 'default']

    # B. Data for the 'prefer_scion' strategy.
    df_scion = df_plot[df_plot['kademlia_strategy'] == 'prefer_scion'].copy()

    # --- MODIFICATION: Add "attackers" to the legend entries ---
    # Create a new column with the full, desired legend text.
    df_scion['strategy_label'] = 'prefer_scion (' + \
                                 (df_scion['attacker_fraction'] * 100).astype(int).astype(str) + \
                                 '% attackers)'

    # --- Step 3: Create the plot ---
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 7))

    # Plot the 'default' strategy line with its specific label
    sns.lineplot(
        data=df_default,
        x='scion_fraction',
        y='mean_attacker_ratio',
        ax=ax,
        marker='s',
        linestyle='--',
        color='black',
        label='default (all)',
        errorbar='sd'
    )

    # Plot the 'prefer_scion' lines using the new descriptive column for the hue
    sns.lineplot(
        data=df_scion,
        x='scion_fraction',
        y='mean_attacker_ratio',
        ax=ax,
        hue='strategy_label', # Use the new column for the legend
        marker='o',
        palette='viridis_r',
        markersize=10
    )

    # --- Step 4: Formatting for Publication ---

    # --- MODIFICATION: Rename axis labels ---
    ax.set_xlabel("Validator nodes", fontsize=22)
    ax.set_ylabel("Attackers in routing tables", fontsize=22)

    # Set axis limits
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlim(-0.01, 0.22)

    # Set x-axis ticks and labels
    x_tick_locations = np.arange(0, 0.201, 0.05)
    ax.set_xticks(x_tick_locations)
    ax.set_xticklabels([f'{x:.0%}' for x in x_tick_locations], fontsize=20)

    # --- MODIFICATION: Format y-axis ticks as percentages ---
    y_tick_locations = np.arange(0, 1.01, 0.2)
    ax.set_yticks(y_tick_locations)
    ax.set_yticklabels([f'{y:.0%}' for y in y_tick_locations], fontsize=20)


    ax.grid(True, which='both', linestyle='-', linewidth=0.5)

    # --- MODIFICATION: Make the teal curve thicker ---
    # The color depends on the palette and the number/order of unique hue values.
    # We identify the line by its label after plotting and then change its properties.
    # Change the target_label_for_thickening to match the curve you want to be thicker.
    try:
        target_label_for_thickening = 'prefer_scion (10% attackers)'
        for line in ax.lines:
            if line.get_label() == target_label_for_thickening:
                line.set_linewidth(3.5)  # Set a thicker linewidth
    except Exception as e:
        print(f"Could not thicken the curve. Reason: {e}")


    # Customize Legend
    handles, labels = ax.get_legend_handles_labels()
    # Sort legend entries to keep them in a consistent order
    try:
        # Sort by the numeric percentage of attackers in the label
        sorted_legend = sorted(zip(handles, labels),
                               key=lambda x: (
                                   'default' not in x[1], # 'default' comes first
                                   int(x[1][x[1].find("(")+1:x[1].find("%")]) if '%' in x[1] else float('inf')
                               ))
        handles, labels = zip(*sorted_legend)
    except (ValueError, TypeError):
        # Fallback if sorting fails
        pass

    # --- MODIFICATION: Move the legend up by approximately 1em ---
    legend = ax.legend(handles=handles, labels=labels, loc='center left', bbox_to_anchor=(0.489, 0.65))
    legend.set_title('') # Remove the legend title
    plt.setp(legend.get_texts(), fontsize='20')

    # --- Step 5: Save and show the plot ---
    plt.tight_layout()

    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_FILE2, dpi=300, bbox_inches='tight')

    print(f"Final comparison plot saved as '{OUTPUT_FILE}' and '{OUTPUT_FILE2}'")

    plt.show()

if __name__ == '__main__':
    main()