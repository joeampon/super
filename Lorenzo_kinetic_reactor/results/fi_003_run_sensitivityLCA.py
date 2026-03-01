#%%
"""
Análisis de Sensibilidad LCA - Versión con Validación
Incluye comprobaciones y normalización por múltiples productos
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from codigestion_bst_continuos_function import create_and_simulate_system, run_lca_analysis
import biosteam as bst
import os

#%% 1. Configuración de parámetros

# Parámetros base
base_params = {
    "ISR": 2.0,
    "S0": 300000,
    "F_TOTAL": 100000,
    "feedStock_ratio": 0.5,
    "X10_ratio": 0.6,
    "reactor_tau": 48,
    "reactor_T": 330,
    "IRR": 0.10,
    "lang_factor": 2.7,
    "operating_days": 330
}

# Configuración de sensibilidad (valor bajo, valor alto)
# NOTA: F_TOTAL eliminado porque solo escala el proceso sin cambiar
#       la intensidad de impacto por kg de producto
parameters_config = {
    "reactor_tau": (24, 96),           # Tiempo de residencia (h) - afecta conversión
    "ISR": (1.5, 2.5),                 # Ratio inóculo/sustrato - afecta eficiencia
    "S0": (250000, 350000),            # Concentración VS ±15% - afecta conversión
    "feedStock_ratio": (0.3, 0.7),     # Fracción de SW - diferentes impactos SW vs DW
    "X10_ratio": (0.4, 0.8),           # Fracción de X1 en inóculo - afecta microbiología
}

# Etiquetas para gráficos
parameter_labels = {
    "reactor_tau": "Residence Time \n [24-96h]",
    "ISR": "ISR \n [1.5-2.5]",
    "S0": "VS Concentration \n [250-350 g/L]",
    "feedStock_ratio": "SHW Fraction \n [0.3-0.7]",
    "X10_ratio": "X1 Biomass Fraction in BM \n [0.4-0.8]"
}

# Productos para normalizar (unidad funcional)
functional_units = ['rng']  # Solo RNG, sin biochar

print("="*80)
print("CONFIGURACIÓN DEL ANÁLISIS DE SENSIBILIDAD LCA CON VALIDACIÓN")
print("="*80)
print(f"\nParámetros base:")
for k, v in base_params.items():
    print(f"  {k}: {v}")

print(f"\nRangos de sensibilidad:")
for k, v in parameters_config.items():
    print(f"  {k}: {v[0]} - {v[1]}")

print(f"\nUnidades funcionales:")
for fu in functional_units:
    print(f"  - {fu}")

#%% 2. Función de validación

def validate_system_state(system, iteration_name):
    """
    Valida que el sistema está correctamente inicializado.
    """
    print(f"\n  🔍 Validando sistema para {iteration_name}:")

    # Verificar que el flowsheet fue limpiado
    flowsheet_id = id(bst.main_flowsheet)
    print(f"    - Flowsheet ID: {flowsheet_id}")

    # Verificar número de streams
    n_feeds = len(system.feeds)
    n_products = len(system.products)
    print(f"    - Feeds: {n_feeds}, Products: {n_products}")

    # Verificar IDs de streams principales
    feed_ids = [s.ID for s in system.feeds]
    product_ids = [s.ID for s in system.products]
    print(f"    - Feed IDs: {feed_ids}")
    print(f"    - Product IDs: {product_ids}")

    # Verificar que las streams son objetos nuevos
    feed_mem_ids = [id(s) for s in system.feeds]
    print(f"    - Feed memory IDs: {[f'{x:x}' for x in feed_mem_ids]}")

    return {
        'flowsheet_id': flowsheet_id,
        'n_feeds': n_feeds,
        'n_products': n_products,
        'feed_ids': feed_ids,
        'product_ids': product_ids,
        'feed_memory_ids': feed_mem_ids
    }

#%% 3. Caso base con validación

print("\n" + "="*80)
print("EJECUTANDO CASO BASE")
print("="*80)

system_base, tea_base, streams_base, lca_manager_base = create_and_simulate_system(
    **base_params,
    setup_lca=True
)

# Validar caso base
validation_base = validate_system_state(system_base, "BASE CASE")

# Obtener productos
products = {}
for fu in functional_units:
    if fu in streams_base:
        products[fu] = streams_base[fu]
        print(f"\n✓ Producto '{fu}' encontrado: {products[fu].F_mass:.4f} kg/hr")
    else:
        print(f"\n⚠️  Producto '{fu}' NO encontrado en streams")

# Obtener categorías de impacto
categories = lca_manager_base.get_indicators_category

# Calcular impactos base case usando run_lca_analysis
print(f"\nCalculando impactos base case con run_lca_analysis...")
total_impacts_base, _,_ = run_lca_analysis(system_base, streams_base, lca_manager_base)

basecase_impacts = {}
for fu in functional_units:
    if fu in products:
        basecase_impacts[fu] = {}
        product_flow = system_base.get_mass_flow(products[fu])

        print(f"\nImpactos base case por kg de {fu.upper()}:")
        print(f"  (Flujo de {fu}: {product_flow:.4f} kg/hr)")

        for category in categories:
            # Usar el valor calculado por run_lca_analysis
            basecase_impacts[fu][category] = total_impacts_base.get(category, 0)
            print(f"    {category}: {basecase_impacts[fu][category]:.6e}")

print(f"\n✓ Base case calculado para {len(functional_units)} productos")
print(f"✓ Categorías de impacto: {len(categories)}")

#%% 4. Análisis de sensibilidad con validaciones

# Estructura para almacenar resultados por producto
results = {fu: {cat: {} for cat in categories} for fu in functional_units}

# Almacenar validaciones
validations = {'base': validation_base}

print("\n" + "="*80)
print("EJECUTANDO ANÁLISIS DE SENSIBILIDAD CON VALIDACIONES")
print("="*80)

for param_name, (low_val, high_val) in parameters_config.items():
    print(f"\n{'='*80}")
    print(f"Parámetro: {param_name}")
    print(f"  Valor bajo:  {low_val}")
    print(f"  Valor alto:  {high_val}")
    print(f"{'='*80}")

    try:
        # === CASO BAJO ===
        print(f"\n  → Simulando caso BAJO ({param_name} = {low_val})...")
        params_low = base_params.copy()
        params_low[param_name] = low_val

        sys_low, tea_low, str_low, lca_mgr_low = create_and_simulate_system(
            **params_low,
            setup_lca=True
        )

        # Validar caso bajo
        val_key_low = f"{param_name}_low"
        validations[val_key_low] = validate_system_state(sys_low, f"{param_name}=LOW")

        # === CASO ALTO ===
        print(f"\n  → Simulando caso ALTO ({param_name} = {high_val})...")
        params_high = base_params.copy()
        params_high[param_name] = high_val

        sys_high, tea_high, str_high, lca_mgr_high = create_and_simulate_system(
            **params_high,
            setup_lca=True
        )

        # Validar caso alto
        val_key_high = f"{param_name}_high"
        validations[val_key_high] = validate_system_state(sys_high, f"{param_name}=HIGH")

        # === CALCULAR IMPACTOS PARA CADA PRODUCTO ===
        print("\n  → Calculando impactos por producto con run_lca_analysis...")

        # Calcular impactos usando run_lca_analysis para LOW y HIGH
        total_impacts_low, _ = run_lca_analysis(sys_low, str_low, lca_mgr_low)
        total_impacts_high, _ = run_lca_analysis(sys_high, str_high, lca_mgr_high)

        for fu in functional_units:
            if fu in str_low and fu in str_high:
                product_low = str_low[fu]
                product_high = str_high[fu]

                flow_low = sys_low.get_mass_flow(product_low)
                flow_high = sys_high.get_mass_flow(product_high)

                print(f"\n    Producto: {fu}")
                print(f"      Flujo LOW:  {flow_low:.4f} kg/hr")
                print(f"      Flujo HIGH: {flow_high:.4f} kg/hr")

                for category in categories:
                    impact_low = total_impacts_low.get(category, 0)
                    impact_high = total_impacts_high.get(category, 0)

                    results[fu][category][param_name] = [impact_low, impact_high]

        print(f"\n  ✓ Completado para {param_name}")

    except Exception as e:
        print(f"\n  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

        for fu in functional_units:
            for category in categories:
                results[fu][category][param_name] = [None, None]

print("\n" + "="*80)
print("✓ ANÁLISIS DE SENSIBILIDAD COMPLETADO")
print("="*80)

#%% 5. Reporte de validaciones

print("\n" + "="*80)
print("REPORTE DE VALIDACIONES")
print("="*80)

print("\nVerificación de que cada simulación inicia desde cero:")
print("\nFlowsheet IDs (deben ser diferentes si se reinicia correctamente):")

flowsheet_ids = [v['flowsheet_id'] for v in validations.values()]
unique_flowsheet_ids = len(set(flowsheet_ids))

for k, v in validations.items():
    print(f"  {k:30s}: Flowsheet ID = {v['flowsheet_id']}, Feeds = {v['n_feeds']}, Products = {v['n_products']}")

if unique_flowsheet_ids == 1:
    print("\n✓ CORRECTO: Todos usan el mismo flowsheet (reiniciado con clear())")
else:
    print(f"\n⚠️  ADVERTENCIA: Se encontraron {unique_flowsheet_ids} flowsheets diferentes")

print("\nVerificación de memoria de streams (deben cambiar en cada iteración):")
base_feed_ids = validations['base']['feed_memory_ids']
print(f"\nBase case feed memory IDs: {[f'{x:x}' for x in base_feed_ids]}")

for k, v in list(validations.items())[1:3]:  # Mostrar primeras 2 iteraciones
    current_feed_ids = v['feed_memory_ids']
    print(f"{k:30s}: {[f'{x:x}' for x in current_feed_ids]}")

    if any(x in base_feed_ids for x in current_feed_ids):
        print(f"  ⚠️  PROBLEMA: Algunas streams tienen la misma dirección de memoria")
    else:
        print(f"  ✓ CORRECTO: Streams nuevas en cada iteración")

#%% 6. Función mejorada para tornado plots

def plot_tornado_lca_by_product(product, category, results_dict, basecase_value,
                                 param_labels=None, save_path=None):
    """
    Crea un tornado plot para una categoría de impacto LCA normalizada por producto.
    """
    if category not in results_dict:
        print(f"Categoría '{category}' no encontrada")
        return None

    category_results = results_dict[category]
    basecase = basecase_value

    # Filtrar resultados válidos
    valid_results = {k: v for k, v in category_results.items() if None not in v}

    if not valid_results:
        print(f"No hay resultados válidos para '{category}' (producto: {product})")
        return None

    # Ordenar por desviación máxima
    sorted_results = dict(sorted(
        valid_results.items(),
        key=lambda item: max(abs(item[1][0] - basecase), abs(item[1][1] - basecase)),
        reverse=True
    ))

    # Preparar datos
    if param_labels is None:
        labels = list(sorted_results.keys())
    else:
        labels = [param_labels.get(k, k) for k in sorted_results.keys()]

    lows = [v[0] for v in sorted_results.values()]
    highs = [v[1] for v in sorted_results.values()]

    # Crear gráfico con tamaño aumentado
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10, 5))

    # Barras
    ax.barh(y, [(lo - basecase)/basecase for lo in lows],
            color="steelblue", label="Low", alpha=0.8)
    ax.barh(y, [(hi - basecase)/basecase for hi in highs],
            color="orange", label="High", alpha=0.8)

    # Línea base
    ax.axvline(0, color="red", linestyle="--", linewidth=1)
               #label=f"Base = {basecase:.2e}")

    #Anotaciones con fuente más grande y mejor espaciado
    # for i, (lo, hi) in enumerate(zip(lows, highs)):
    #     #Calcular offset para evitar solapamiento
    #     x_range = max(highs) - min(lows)
    #     offset = x_range * 0.02  # 2% del rango

    #     ax.text(lo - offset, i, f"{(lo-basecase)/basecase:.1e}", va="center", ha="right",
    #             fontsize=18, color="black", weight="bold",
    #             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='none'))
    #     ax.text(hi + offset, i, f"{(hi-basecase)/basecase:.1e}", va="center", ha="left",
    #             fontsize=18, color="black", weight="bold",
    #             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='none'))

    # Formato con fuentes más grandes
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=14)
    ax.set_xlabel(f"ratio {category} (Base = {basecase:.2e})", fontsize=18, weight='bold')
    #ax.set_title(f"Tornado: {category}\n(per kg {product.upper()})", fontsize=18, weight="bold", pad=20)
    ax.legend(fontsize=18, loc='best', framealpha=0.9)
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.tick_params(axis='x', labelsize=18)
    ax.invert_yaxis()

    plt.tight_layout(pad=1.5)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"    Guardado: {save_path}")

    plt.show()

    return fig

#%% 7. Generar tornado plots para cada producto

save_dir = 'results/lca_sensitivity'
os.makedirs(save_dir, exist_ok=True)

print("\n" + "="*80)
print("GENERANDO TORNADO PLOTS POR PRODUCTO")
print("="*80)

for fu in functional_units:
    print(f"\n{'='*80}")
    print(f"PRODUCTO: {fu.upper()}")
    print(f"{'='*80}")

    # Crear subdirectorio para este producto
    product_dir = f"{save_dir}/{fu}"
    os.makedirs(product_dir, exist_ok=True)

    for i, category in enumerate(categories, 1):
        print(f"  [{i}/{len(categories)}] {category}")

        # Crear nombre de archivo seguro
        safe_filename = category.replace('/', '_').replace('\\', '_').replace(' ', '_')
        save_path = f"{product_dir}/tornado_{safe_filename}.png"

        # Generar plot
        plot_tornado_lca_by_product(
            fu,
            category,
            results[fu],
            basecase_impacts[fu][category],
            param_labels=parameter_labels,
            save_path=save_path
        )

print("\n" + "="*80)
print(f"✓ COMPLETADO - Gráficos guardados en: {save_dir}")
print("="*80)

#%% 8. Exportar resultados a CSV por producto

for fu in functional_units:
    print(f"\nExportando resultados para {fu.upper()}...")

    # Crear DataFrame con resultados
    results_data = []

    for category in categories:
        for param, (low, high) in results[fu][category].items():
            if low is not None and high is not None:
                base_val = basecase_impacts[fu][category]
                results_data.append({
                    'Product': fu,
                    'Category': category,
                    'Parameter': param,
                    'Base_Case': base_val,
                    'Low_Value': low,
                    'High_Value': high,
                    'Range': abs(high - low),
                    'Percent_Change': abs(high - low) / abs(base_val) * 100 if base_val != 0 else 0
                })

    df_results = pd.DataFrame(results_data)

    # Guardar a CSV
    csv_path = f'{save_dir}/{fu}/sensitivity_results.csv'
    df_results.to_csv(csv_path, index=False)

    print(f"  ✓ Resultados guardados en: {csv_path}")

#%% 9. Resumen comparativo entre productos

print("\n" + "="*80)
print("RESUMEN COMPARATIVO ENTRE PRODUCTOS")
print("="*80)

comparison_data = []

for category in categories:
    for fu in functional_units:
        max_range = 0
        most_sensitive_param = None

        for param, (low, high) in results[fu][category].items():
            if low is not None and high is not None:
                param_range = abs(high - low)
                if param_range > max_range:
                    max_range = param_range
                    most_sensitive_param = param

        comparison_data.append({
            'Category': category,
            'Product': fu,
            'Most_Sensitive_Parameter': most_sensitive_param,
            'Max_Range': max_range,
            'Base_Case_Value': basecase_impacts[fu][category]
        })

df_comparison = pd.DataFrame(comparison_data)
df_comparison = df_comparison.sort_values(['Category', 'Product'])

print("\nParámetros más sensibles por categoría y producto:")
print(df_comparison.to_string(index=False))

# Guardar comparación
comparison_path = f'{save_dir}/product_comparison.csv'
df_comparison.to_csv(comparison_path, index=False)
print(f"\n✓ Comparación guardada en: {comparison_path}")

print("\n" + "="*80)
print("✓✓✓ ANÁLISIS COMPLETO FINALIZADO CON VALIDACIONES ✓✓✓")
print("="*80)
