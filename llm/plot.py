import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set up enhanced visualization style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("viridis")
plt.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 16,
    'axes.titleweight': 'bold',
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 12,
    'figure.titlesize': 18
})

def parse_coffee_data(filename):
    """
    Load the coffee data and parse the ESP commands correctly.
    Extracts the first occurrence of each parameter type.
    """
    # Read the CSV file
    df = pd.read_csv(filename)
    
    # Create new columns for each command parameter
    df['Delay_seconds'] = 0
    df['RPM_percentage'] = 0
    df['Volume_ml'] = 180  # Default value
    df['Grind_size'] = 0
    
    # Parse each ESP command to extract the first occurrence of each parameter
    for i, row in df.iterrows():
        command = row['esp_command']
        parts = command.split(' ')
        
        # Extract parameters by type
        for part in parts:
            try:
                key, value = part.split('-')
                value = float(value)
                
                # Store the first occurrence of each parameter type
                if key == 'D' and df.at[i, 'Delay_seconds'] == 0:
                    df.at[i, 'Delay_seconds'] = value
                elif key == 'R' and df.at[i, 'RPM_percentage'] == 0:
                    df.at[i, 'RPM_percentage'] = value
                elif key == 'V' and df.at[i, 'Volume_ml'] == 180:
                    df.at[i, 'Volume_ml'] = value
                elif key == 'G' and df.at[i, 'Grind_size'] == 0:
                    df.at[i, 'Grind_size'] = value
            except ValueError:
                continue  # Skip malformed parts
    
    # Create a nicer category name for display
    df['Category'] = df['category'].str.replace('_', ' ').str.title()
    
    # Copy flavor_profile to a separate column for visualization
    if 'flavor_profile' in df.columns:
        df['Flavor_Profile'] = df['flavor_profile']
    
    return df

def create_coffee_profile_chart(df, output_folder):
    """
    Create a comprehensive visualization of coffee brewing profiles
    showing all parameters together for easy comparison.
    """
    # Calculate the mean values for each parameter by category
    profile_data = df.groupby('Category')[
        ['Delay_seconds', 'RPM_percentage', 'Volume_ml', 'Grind_size']
    ].mean().reset_index()
    
    # Set a specific order for categories
    category_order = ['Bold Espresso', 'Chocolate Nutty', 'Fruity Light', 'Iced Sweet', 'Smooth Creamy']
    profile_data['Category'] = pd.Categorical(profile_data['Category'], categories=category_order, ordered=True)
    profile_data = profile_data.sort_values('Category')
    
    # Create a figure with subplots
    fig, axs = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Coffee Brewing Profiles by Category', fontsize=20, fontweight='bold', y=0.98)
    
    # Flatten the axes array for easier iteration
    axs = axs.flatten()
    
    # Plot each parameter
    params = [
        ('Delay_seconds', 'Delay Time (seconds)', 0),
        ('RPM_percentage', 'Motor Speed (%)', 1),
        ('Grind_size', 'Grind Size (1=Fine, 5=Coarse)', 2),
        ('Volume_ml', 'Volume (ml)', 3)
    ]
    
    # Define custom colors for each category
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for (param, title, idx) in params:
        ax = axs[idx]
        bars = ax.bar(profile_data['Category'], profile_data[param], color=colors)
        
        # Add value labels on top of each bar
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.1f}', ha='center', va='bottom', fontweight='bold')
        
        # Set titles and labels
        ax.set_title(title)
        ax.set_xlabel('Coffee Category')
        ax.set_ylabel(param.replace('_', ' '))
        
        # Rotate x-labels for better readability
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # Add grid lines for better readability
        ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)
    
    # Save the figure
    plt.savefig(f'{output_folder}/coffee_profile_chart.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_radar_chart(df, output_folder):
    """
    Create a radar chart to visualize the coffee profile parameters.
    """
    # Calculate mean values for each parameter by category
    profile_data = df.groupby('Category')[
        ['Delay_seconds', 'RPM_percentage', 'Grind_size']
    ].mean()
    
    # Normalize the data to a 0-1 scale for the radar chart
    normalized_data = profile_data.copy()
    for col in normalized_data.columns:
        min_val = normalized_data[col].min()
        max_val = normalized_data[col].max()
        if max_val > min_val:  # Avoid division by zero
            normalized_data[col] = (normalized_data[col] - min_val) / (max_val - min_val)
    
    # Set up the radar chart
    categories = ['Delay Time', 'Motor Speed', 'Grind Size']
    N = len(categories)
    
    # Create a figure
    fig, ax = plt.figure(figsize=(10, 10)), plt.subplot(111, polar=True)
    
    # Set the angle for each parameter (evenly spaced)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Close the loop
    
    # Set the labels for each parameter
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    
    # Draw the chart for each coffee category
    for i, category in enumerate(profile_data.index):
        values = normalized_data.loc[category].values.flatten().tolist()
        values += values[:1]  # Close the loop
        
        # Plot the values
        ax.plot(angles, values, linewidth=2, linestyle='solid', label=category)
        ax.fill(angles, values, alpha=0.1)
    
    # Add legend
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    
    plt.title('Coffee Brewing Parameters Comparison', size=20, y=1.05)
    
    # Save the figure
    plt.savefig(f'{output_folder}/coffee_radar_chart.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_heatmap(df, output_folder):
    """
    Create a heatmap showing the brewing parameters for each coffee category.
    """
    # Calculate mean values for each parameter by category
    profile_data = df.groupby('Category')[
        ['Delay_seconds', 'RPM_percentage', 'Grind_size']
    ].mean()
    
    # Create a heatmap
    plt.figure(figsize=(12, 8))
    ax = sns.heatmap(profile_data, annot=True, fmt='.1f', cmap='viridis', 
                    linewidths=0.5, cbar_kws={'label': 'Parameter Value'})
    
    # Set titles and labels
    plt.title('Coffee Brewing Parameter Heatmap', size=18)
    plt.tight_layout()
    
    # Save the figure
    plt.savefig(f'{output_folder}/coffee_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_scatter_matrix(df, output_folder):
    """
    Create a scatter matrix to visualize relationships between brewing parameters.
    """
    # Select the relevant columns
    plot_data = df[['Category', 'Delay_seconds', 'RPM_percentage', 'Grind_size']]
    
    # Create the scatter matrix
    plt.figure(figsize=(12, 10))
    scatter_grid = sns.pairplot(plot_data, hue='Category', height=3, 
                               diag_kind='kde', plot_kws={'alpha': 0.6, 's': 80})
    
    scatter_grid.fig.suptitle('Relationships Between Coffee Brewing Parameters', 
                             size=16, y=1.02)
    
    # Save the figure
    plt.savefig(f'{output_folder}/coffee_scatter_matrix.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_3d_scatter(df, output_folder):
    """
    Create a 3D scatter plot showing the relationship between
    Delay, RPM, and Grind Size.
    """
    try:
        from mpl_toolkits.mplot3d import Axes3D
        
        # Create a 3D scatter plot
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Get unique categories and define colors
        categories = df['Category'].unique()
        colors = plt.cm.viridis(np.linspace(0, 1, len(categories)))
        
        # Plot each category
        for i, category in enumerate(categories):
            category_data = df[df['Category'] == category]
            ax.scatter(category_data['Delay_seconds'], 
                      category_data['RPM_percentage'], 
                      category_data['Grind_size'],
                      c=[colors[i]], label=category, s=100, alpha=0.7)
        
        # Set labels and title
        ax.set_xlabel('Delay (seconds)', fontsize=12)
        ax.set_ylabel('RPM (%)', fontsize=12)
        ax.set_zlabel('Grind Size', fontsize=12)
        plt.title('3D Visualization of Coffee Brewing Parameters', size=16)
        
        # Add legend
        ax.legend()
        
        # Save the figure
        plt.savefig(f'{output_folder}/coffee_3d_scatter.png', dpi=300, bbox_inches='tight')
        plt.close()
    except ImportError:
        print("3D plotting requires mpl_toolkits.mplot3d. Skipping 3D scatter plot.")

def create_coffee_recipe_cards(df, output_folder):
    """
    Create visual recipe cards for each coffee category.
    """
    # Calculate mean values for each parameter by category
    recipe_data = df.groupby('Category')[
        ['Delay_seconds', 'RPM_percentage', 'Volume_ml', 'Grind_size']
    ].mean().reset_index()
    
    # Get unique categories
    categories = recipe_data['Category'].tolist()
    
    # Create a figure with subplots (one per category)
    fig, axs = plt.subplots(len(categories), 1, figsize=(10, 4*len(categories)))
    
    # If there's only one category, make axs an array
    if len(categories) == 1:
        axs = [axs]
    
    # Define color mappings for grind size
    grind_colors = {1.0: '#8B4513', 5.0: '#D2B48C'}  # Dark brown for fine, light brown for coarse
    
    # Define labels for parameters
    param_labels = {
        'Delay_seconds': 'Delay',
        'RPM_percentage': 'Motor Speed',
        'Volume_ml': 'Volume',
        'Grind_size': 'Grind'
    }
    
    # Define units for parameters
    param_units = {
        'Delay_seconds': 'sec',
        'RPM_percentage': '%',
        'Volume_ml': 'ml',
        'Grind_size': ''
    }
    
    # Define grind descriptions
    grind_desc = {1.0: 'Fine', 5.0: 'Coarse'}
    
    for i, category in enumerate(categories):
        ax = axs[i]
        cat_data = recipe_data[recipe_data['Category'] == category]
        
        # Turn off axis
        ax.axis('off')
        
        # Add a background rectangle
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=True, color='#F5F5F5', 
                                  transform=ax.transAxes, zorder=-1))
        
        # Add category title
        ax.text(0.5, 0.92, category, ha='center', va='top', fontsize=18, 
               fontweight='bold', transform=ax.transAxes)
        
        # Add divider line
        ax.axhline(y=0.85, xmin=0.05, xmax=0.95, color='black', alpha=0.3)
        
        # Add recipe parameters
        params = ['Delay_seconds', 'RPM_percentage', 'Volume_ml', 'Grind_size']
        y_positions = [0.7, 0.55, 0.4, 0.25]
        
        for j, (param, y_pos) in enumerate(zip(params, y_positions)):
            value = cat_data[param].values[0]
            
            # Add parameter label
            ax.text(0.2, y_pos, f"{param_labels[param]}:", ha='right', va='center', 
                   fontsize=14, transform=ax.transAxes)
            
            # Add parameter value
            if param == 'Grind_size':
                value_text = f"{value:.0f} ({grind_desc[value]})"
                circle_color = grind_colors[value]
                
                # Add colored circle for grind size
                ax.add_patch(plt.Circle((0.35, y_pos), 0.03, color=circle_color, 
                                       transform=ax.transAxes))
                
                ax.text(0.45, y_pos, value_text, ha='left', va='center', 
                       fontsize=14, fontweight='bold', transform=ax.transAxes)
            else:
                ax.text(0.35, y_pos, f"{value:.1f} {param_units[param]}", ha='left', 
                       va='center', fontsize=14, fontweight='bold', transform=ax.transAxes)
        
        # Add a visual motor speed indicator
        rpm = cat_data['RPM_percentage'].values[0]
        rpm_norm = rpm / 100.0  # Normalize to 0-1
        ax.add_patch(plt.Rectangle((0.6, 0.535), 0.25, 0.03, fill=True, color='#E0E0E0'))
        ax.add_patch(plt.Rectangle((0.6, 0.535), 0.25 * rpm_norm, 0.03, fill=True, color='#1f77b4'))
        
        # Add border
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor='black', 
                                  linewidth=2, transform=ax.transAxes))
    
    plt.tight_layout()
    
    # Save the figure
    plt.savefig(f'{output_folder}/coffee_recipe_cards.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_param_correlation_chart(df, output_folder):
    """
    Create a chart showing the correlation between coffee parameters and categories.
    """
    # Create dummy variables for categories
    category_dummies = pd.get_dummies(df['Category'])
    
    # Join with the main parameters
    corr_data = pd.concat([
        df[['Delay_seconds', 'RPM_percentage', 'Grind_size']], 
        category_dummies
    ], axis=1)
    
    # Calculate correlation matrix
    corr_matrix = corr_data.corr()
    
    # Create a heatmap
    plt.figure(figsize=(12, 10))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    ax = sns.heatmap(corr_matrix, mask=mask, cmap='coolwarm', annot=True, 
                    fmt='.2f', square=True, linewidths=.5, cbar_kws={'label': 'Correlation'})
    
    # Set titles and labels
    plt.title('Correlation Between Coffee Parameters and Categories', size=16)
    plt.tight_layout()
    
    # Save the figure
    plt.savefig(f'{output_folder}/parameter_correlation.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_coffee_recipes_table(df):
    """
    Create a summary table of coffee recipes.
    """
    # Group by category and calculate mean/std for each parameter
    recipe_means = df.groupby('Category')[
        ['Delay_seconds', 'RPM_percentage', 'Volume_ml', 'Grind_size']
    ].mean().round(1)
    
    recipe_std = df.groupby('Category')[
        ['Delay_seconds', 'RPM_percentage', 'Volume_ml', 'Grind_size']
    ].std().round(2)
    
    # Rename columns for clarity
    recipe_means.columns = ['Delay (sec)', 'RPM (%)', 'Volume (ml)', 'Grind Size']
    recipe_std.columns = ['Delay StdDev', 'RPM StdDev', 'Volume StdDev', 'Grind StdDev']
    
    # Convert grind size to descriptive text
    grind_descriptions = {1.0: 'Fine', 5.0: 'Coarse'}
    recipe_means['Grind Description'] = recipe_means['Grind Size'].map(grind_descriptions)
    
    # Count the number of entries in each category
    recipe_means['Sample Count'] = df.groupby('Category').size()
    
    # Combine means and standard deviations
    recipes = pd.concat([recipe_means, recipe_std], axis=1)
    
    # Reorder columns for better presentation
    col_order = ['Delay (sec)', 'Delay StdDev', 'RPM (%)', 'RPM StdDev', 
                'Volume (ml)', 'Volume StdDev', 'Grind Size', 'Grind StdDev', 
                'Grind Description', 'Sample Count']
    
    recipes = recipes[col_order]
    
    return recipes

def generate_coffee_analysis(filename, output_folder='coffee_analysis'):
    """
    Generate a comprehensive analysis of coffee brewing data.
    """
    print(f"Generating coffee analysis from {filename}...")
    
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Load and parse the data
    df = parse_coffee_data(filename)
    
    # Show basic info
    print(f"Analyzed {len(df)} coffee brew records across {df['Category'].nunique()} categories")
    
    # Create recipe table
    recipes = create_coffee_recipes_table(df)
    print("\n===== Coffee Brewing Recipes =====")
    print(recipes)
    
    # Save recipe table to CSV
    recipes.to_csv(f'{output_folder}/coffee_recipes.csv')
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    create_coffee_profile_chart(df, output_folder)
    create_radar_chart(df, output_folder)
    create_heatmap(df, output_folder)
    create_scatter_matrix(df, output_folder)
    create_3d_scatter(df, output_folder)
    create_coffee_recipe_cards(df, output_folder)
    create_param_correlation_chart(df, output_folder)
    
    print(f"Analysis complete! All results saved to {output_folder}/ folder")
    
    return df, recipes

# Main execution
if __name__ == "__main__":
    # Specify your CSV file path
    file_path = "coffee_brew_results.csv"
    
    # Run the analysis
    df, recipes = generate_coffee_analysis(file_path)