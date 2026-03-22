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