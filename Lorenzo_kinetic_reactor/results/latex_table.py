"""
Simple LaTeX table generator from pandas DataFrames.
"""

import pandas as pd
import os
from codigestion_bst_continuos_function import create_and_simulate_system, energy_balance, equipment_costs


class LaTeXTable:
    """
    Generate LaTeX tables from pandas DataFrames.

    Example:
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        table = LaTeXTable(df, caption="My table", label="tab:mytable",
                          column_format='lc', float_format='%.3f')
        table.save("output")
    """

    def __init__(self, data, caption="", label="", output_dir='results',
                 column_format=None, float_format='%.2f', filename=None):
        """
        Args:
            data: pd.DataFrame or dict
            caption: Table caption
            label: Table label for references
            output_dir: Output directory
            column_format: Column alignment (e.g., 'lc', 'lrrr')
            float_format: Number format (e.g., '%.2f', '%.3f')
            filename: If provided, auto-saves on creation
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        if isinstance(data, dict):
            self.df = pd.DataFrame.from_dict(data, orient='index', columns=['Value'])
            self.df.index.name = 'Parameter'
        else:
            self.df = data.copy()

        self.caption = caption
        self.label = label
        self.column_format = column_format
        self.float_format = float_format

        # Auto-save if filename provided
        if filename:
            self.save(filename)

    def to_latex(self, column_format=None, float_format=None, include_index=True):
        """Generate LaTeX code."""
        # Use instance defaults if not specified
        if column_format is None:
            column_format = self.column_format
        if column_format is None:
            n_cols = len(self.df.columns) + (1 if include_index else 0)
            column_format = 'l' + 'c' * (n_cols - 1)

        if float_format is None:
            float_format = self.float_format

        latex = "\\begin{table}[h]\n\\centering\n"

        if self.caption:
            latex += f"\\caption{{{self.caption}}}\n"
        if self.label:
            latex += f"\\label{{{self.label}}}\n"

        latex += f"\\begin{{tabular}}{{{column_format}}}\n\\hline\n"

        # Headers
        headers = []
        if include_index:
            headers.append(f"\\textbf{{{self.df.index.name or ''}}}")
        headers.extend([f"\\textbf{{{col}}}" for col in self.df.columns])
        latex += " & ".join(headers) + " \\\\\n\\hline\n"

        # Rows
        for idx, row in self.df.iterrows():
            row_data = [str(idx)] if include_index else []
            for val in row:
                if isinstance(val, (int, float)):
                    try:
                        row_data.append(float_format % val)
                    except:
                        row_data.append(str(val))
                else:
                    row_data.append(str(val))
            latex += " & ".join(row_data) + " \\\\\n"

        latex += "\\hline\n\\end{tabular}\n\\end{table}\n"
        return latex

    def save(self, filename, column_format=None, float_format=None, include_index=True):
        """Save as .tex and .csv"""
        tex_path = os.path.join(self.output_dir, f"{filename}.tex")
        csv_path = os.path.join(self.output_dir, f"{filename}.csv")

        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(self.to_latex(
                column_format=column_format,
                float_format=float_format,
                include_index=include_index
            ))

        self.df.to_csv(csv_path, index=include_index)
        return tex_path, csv_path

    def __str__(self):
        return self.to_latex()


# Backward compatibility wrapper
class LaTeXTableGenerator:
    def __init__(self, output_dir='results'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_table(self, df, caption, label, column_format='lc',
                      filename=None, float_format='%.2f'):
        table = LaTeXTable(df, caption=caption, label=label, output_dir=self.output_dir)
        latex_code = table.to_latex(column_format=column_format,
                                     float_format=float_format,
                                     include_index=False)

        csv_path = None
        if filename:
            tex_path = os.path.join(self.output_dir, f"{filename}.tex")
            csv_path = os.path.join(self.output_dir, f"{filename}.csv")
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(latex_code)
            df.to_csv(csv_path, index=False)

        return latex_code, csv_path

if __name__ == "__main__":
    # Example usage
    
    system, tea, streams, lca_manager = create_and_simulate_system()   
    
    # Get TEA parameters
    data_tea = tea.get_tea_parameters
    df_tea = pd.DataFrame.from_dict(data_tea, orient='index', columns=['Value'])
    
    df_tea.index.name = 'Parameter'
    
    table_tea = LaTeXTable(df_tea, 
                           caption="TEA Parameters", label="tab:tea_parameters",
                           column_format='lc', float_format='%.1f')
    
    table_tea.save("tea_parameters_v2")
    
    
    prices = {
        'Bovine manure, \\si{\\usd.\\ton^{-1}}':[ streams['I_feed'].price, 'Cost'],
        
        'Slaughterhouse waste, \\si{\\usd.\\ton^{-1}}':[streams['SW_feed'].price, 'Cost'],
        
        'Domestic waste, \\si{\\usd.\\ton^{-1}}': [streams['DW_feed'].price, 'Cost'],
        
        'Monoethanolamine, \\si{\\usd.\\ton^{-1}}': [streams['mea_fresh'].price, 'Cost'],
        
        'Biochar, \\si{\\usd.\\ton^{-1}}': [streams['biochar'].price, 'Revenue'],
        
        'Natural gas, \\si{\\usd.\\kg^{-1}}': [0.245, 'Cost'],
        
        'Electricity, \\si{\\usd.\\kWh^{-1}}': [system.power_utility.price, 'Cost'],
    }
    
    df_prices = pd.DataFrame.from_dict(prices, orient='index', columns=['Price', 'Type'])
    df_prices.index.name = 'Stream'

    table_prices = LaTeXTable(df_prices, 
                              caption="Stream Prices", label="tab:stream_prices",
                              column_format='lc', float_format='%.3f')
    
    table_prices.save("stream_prices_v2")
    
    data_energy = energy_balance(tea)
  
    df_energy = pd.DataFrame(data_energy)   

  
    
    table_energy = LaTeXTable(df_energy, 
                              caption="Energy Balance", label="tab:energy_balance",
                              column_format='lccc', float_format='%.2f')
    
    table_energy.save("energy_balance_v2", include_index=False)
    
    data_equipment_costs = equipment_costs(tea)
    
    df_equipment_costs = pd.DataFrame(data_equipment_costs)   

    table_equipment_costs = LaTeXTable      (df_equipment_costs, 
                              caption="Equipment Costs", label="tab:equipment_costs",
                              column_format='lcc', float_format='%.2f')
    table_equipment_costs.save("equipment_costs_v2", include_index=False)

    
        