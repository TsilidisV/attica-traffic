import matplotlib.pyplot as plt
import numpy as np

plt.style.use("dark_background")

def plot_actual_vs_predicted(y_true, y_pred):
    """
    Generates an Actual vs. Predicted scatter plot with a dark background theme.
    """

    fig, ax = plt.subplots(figsize=(8, 8))

    # Scatter plot of True vs. Predicted
    ax.scatter(y_true, y_pred, alpha=0.3, edgecolors='none', s=15, label='Model Predictions')

    # Plot the ideal diagonal line (y = x)
    limits = [
        np.min([ax.get_xlim(), ax.get_ylim()]), 
        np.max([ax.get_xlim(), ax.get_ylim()])
    ]
        
    ax.plot(limits, limits, color = 'white', linestyle='--', alpha=0.75, zorder=0, label='Ideal Fit (y=x)')

    # Set labels and title
    ax.set_xlabel("Actual Average Speed (Km/h)", fontsize=12)
    ax.set_ylabel("Predicted Average Speed (Km/h)", fontsize=12)
    ax.set_title("Actual vs. Predicted Values", fontsize=14)
        
    # Make axes equal
    ax.set_aspect('equal')
    ax.set_xlim(limits)
    ax.set_ylim(limits)
        
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.3) # Slightly lower alpha for grid on dark

    plt.close(fig)

    return fig

def plot_actual_vs_predicted_hexbin(y_true, y_pred, gridsize=75, bins=None):
    """
    Generates an Actual vs. Predicted hexbin plot for dense data.
    """
    
    # We make the figure slightly wider (9,8 instead of 8,8) to fit the colorbar
    fig, ax = plt.subplots(figsize=(9, 8))

    # Hexbin plot of True vs. Predicted
    # mincnt=1 ensures we don't color empty hexagons
    # 'inferno' or 'magma' are excellent colormaps for dark themes
    hb = ax.hexbin(
        y_true, y_pred, 
        gridsize=gridsize, 
        cmap='inferno', 
        mincnt=1, 
        edgecolors='none',
        bins=bins
    )

    # Add a colorbar to show the density scale
    cb = fig.colorbar(hb, ax=ax)
    cb.set_label('Count of Points', fontsize=12)

    # Calculate limits for the ideal fit line based on data
    # (Doing this before making axes equal prevents the line from stretching the plot)
    limits = [
        np.min([ax.get_xlim(), ax.get_ylim()]), 
        np.max([ax.get_xlim(), ax.get_ylim()])
    ]
        
    # Plot the ideal diagonal line (y = x)
    # Increased zorder ensures the line draws on top of the hexbins
    ax.plot(limits, limits, color='white', linestyle='--', alpha=0.8, zorder=5, label='Ideal Fit (y=x)')

    # Set labels and title
    ax.set_xlabel("Actual Average Speed (Km/h)", fontsize=12)
    ax.set_ylabel("Predicted Average Speed (Km/h)", fontsize=12)
    ax.set_title("Actual vs. Predicted Values (Density)", fontsize=14)
        
    # Make axes equal and set limits
    ax.set_aspect('equal')
    ax.set_xlim(limits)
    ax.set_ylim(limits)
        
    ax.legend(loc='upper left')
    ax.grid(True, linestyle=':', alpha=0.3) 

    plt.close(fig)

    return fig


def plot_residuals_histogram(y_true, y_pred):
    """
    Plots the distribution of residuals to check for normality with a dark background.
    """
    residuals = y_true - y_pred
    
    # Apply the style temporarily
    fig, ax = plt.subplots(figsize=(8, 6))
        
    ax.hist(residuals, bins=50, density=True, alpha=0.7, color='skyblue', edgecolor='white')
        
    ax.set_xlabel("Residuals (Km/h)", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.set_title("Distribution of Residuals", fontsize=14)
    ax.grid(True, linestyle=':', alpha=0.3)
    
    plt.close(fig)

    return fig