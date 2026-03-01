#%%# python generate random colors
import random
import colorsys
# pyperclip.copy(draw_io(sys))

# install plotly
import plotly.graph_objects as go
from codigestion_bst_continuos_function import create_and_simulate_system


def collapse_passthrough_units(sys, links, limit):
    """
    Collapse units that act as pass-through (no significant mass/composition change).

    A unit is considered pass-through if:
    - It has only one input and one output stream
    - The mass difference between input and output is less than 5% (excluding water)
    - Examples: simple mixers, splitters, heat exchangers without reaction

    Parameters
    ----------
    sys : biosteam.System
        System to analyze
    links : list
        List of links [stream_ID, source_unit, target_unit, value]
    limit : float
        Minimum flow threshold

    Returns
    -------
    list
        Collapsed links with pass-through units removed
    """
    # Identify pass-through units
    passthrough_units = []

    for unit in sys.units:
        # Count non-trivial input and output streams
        ins = [s for s in unit.ins if s and (s.F_mass - s.imass["Water"]) > limit]
        outs = [s for s in unit.outs if s and (s.F_mass - s.imass["Water"]) > limit]

        # Check if unit is a simple pass-through
        if len(ins) == 1 and len(outs) == 1:
            in_stream = ins[0]
            out_stream = outs[0]

            # Calculate mass change (excluding water)
            in_mass = in_stream.F_mass - in_stream.imass["Water"]
            out_mass = out_stream.F_mass - out_stream.imass["Water"]

            if in_mass > 0:
                mass_change_pct = abs(out_mass - in_mass) / in_mass

                # If less than 5% mass change, consider it pass-through
                if mass_change_pct < 0.05:
                    passthrough_units.append(unit.ID)

    # Collapse links that go through pass-through units
    collapsed_links = []

    for link in links:
        stream_id, source, target, value = link

        # If source is a pass-through unit, try to find the real source
        if source in passthrough_units:
            # Find what feeds into this pass-through unit
            feeding_link = next((l for l in links if l[2] == source), None)
            if feeding_link:
                source = feeding_link[1]  # Use the source of the feeding link

        # If target is a pass-through unit, try to find the real target
        if target in passthrough_units:
            # Find what comes out of this pass-through unit
            output_link = next((l for l in links if l[1] == target), None)
            if output_link:
                target = output_link[2]  # Use the target of the output link

        # Only add if not both source and target are pass-through
        if source not in passthrough_units or target not in passthrough_units:
            collapsed_links.append([stream_id, source, target, value])

    # Remove duplicate links that may have been created
    seen = set()
    final_links = []
    for link in collapsed_links:
        key = (link[1], link[2])  # (source, target)
        if key not in seen:
            seen.add(key)
            final_links.append(link)

    print(f"  Collapsed {len(passthrough_units)} pass-through units: {', '.join(passthrough_units) if passthrough_units else 'None'}")

    return final_links


def collapse_passthrough_units_energy(sys, links, limit):
    """
    Collapse units that act as pass-through for energy balance (no significant energy change).

    A unit is considered pass-through if:
    - It has only one input and one output stream
    - The energy (HHV) difference between input and output is less than 5%
    - It has no significant power or heat utilities

    Parameters
    ----------
    sys : biosteam.System
        System to analyze
    links : list
        List of links [stream_ID, source_unit, target_unit, value]
    limit : float
        Minimum energy flow threshold (kJ/hr)

    Returns
    -------
    list
        Collapsed links with pass-through units removed
    """
    # Identify pass-through units
    passthrough_units = []

    for unit in sys.units:
        # Count non-trivial input and output streams
        ins = [s for s in unit.ins if s and s.HHV > limit]
        outs = [s for s in unit.outs if s and s.HHV > limit]

        # Check if unit is a simple pass-through
        if len(ins) == 1 and len(outs) == 1:
            in_stream = ins[0]
            out_stream = outs[0]

            # Calculate energy change
            in_energy = in_stream.HHV
            out_energy = out_stream.HHV

            # Check if unit has significant power or heat utilities
            has_power = False
            has_heat = False
            try:
                if unit.power_utility.rate * 3600 > limit:
                    has_power = True
            except:
                pass

            try:
                if abs(unit.Hnet) > limit:
                    has_heat = True
            except:
                pass

            # If no significant utilities and energy change is small, consider pass-through
            if not has_power and not has_heat and in_energy > 0:
                energy_change_pct = abs(out_energy - in_energy) / in_energy

                # If less than 5% energy change, consider it pass-through
                if energy_change_pct < 0.05:
                    passthrough_units.append(unit.ID)

    # Collapse links that go through pass-through units
    collapsed_links = []

    for link in links:
        stream_id, source, target, value = link

        # Skip utility streams (W_ and Q_) in collapse logic
        if stream_id.startswith('W_') or stream_id.startswith('Q_'):
            collapsed_links.append(link)
            continue

        # If source is a pass-through unit, try to find the real source
        if source in passthrough_units:
            # Find what feeds into this pass-through unit
            feeding_link = next((lnk for lnk in links if lnk[2] == source and not lnk[0].startswith('W_') and not lnk[0].startswith('Q_')), None)
            if feeding_link:
                source = feeding_link[1]  # Use the source of the feeding link

        # If target is a pass-through unit, try to find the real target
        if target in passthrough_units:
            # Find what comes out of this pass-through unit
            output_link = next((lnk for lnk in links if lnk[1] == target and not lnk[0].startswith('W_') and not lnk[0].startswith('Q_')), None)
            if output_link:
                target = output_link[2]  # Use the target of the output link

        # Only add if not both source and target are pass-through
        if source not in passthrough_units or target not in passthrough_units:
            collapsed_links.append([stream_id, source, target, value])

    # Remove duplicate links that may have been created
    seen = set()
    final_links = []
    for link in collapsed_links:
        key = (link[1], link[2])  # (source, target)
        if key not in seen:
            seen.add(key)
            final_links.append(link)

    print(f"  Collapsed {len(passthrough_units)} pass-through units (energy): {', '.join(passthrough_units) if passthrough_units else 'None'}")

    return final_links



def sankeys(sys, scenario="", limit=0, filename="mass_balance_sankey_full.html", save_image=False, name_mapping=None, collapse_units=True):
    """
    Generate mass balance Sankey diagram.

    Parameters
    ----------
    sys : biosteam.System
        System to analyze
    scenario : str
        Scenario name for the title
    limit : float
        Minimum flow (excluding water) to include in diagram
    filename : str
        Output filename (html or png)
    save_image : bool
        If True, tries to save as PNG (requires kaleido/Chrome). If False, saves as HTML.
    name_mapping : dict, optional
        Dictionary to map stream/unit IDs to display names.
        Example: {'R1': 'Reactor', 'slaughterhouse': 'SHW Feed'}
    collapse_units : bool, optional
        If True, collapse units with no significant mass change (pass-through units)
    """
    links = []

    i = 0
    o = 0
    for s in sys.streams:
        if (s.F_mass-s.imass["Water"]) < limit: continue  # Excluding water
        if s.source == None: # input stream
            # links.append([s.ID, f"{i}", s.sink.ID, s.F_mass])
            links.append([s.ID, s.ID, s.sink.ID, s.F_mass-s.imass["Water"]])  # Exclude water
            i += 1
        elif s.sink == None:
            links.append([s.ID, s.source.ID, s.ID, s.F_mass-s.imass["Water"]])  # Exclude water
            o+=1
        else:
            links.append([s.ID, s.source.ID, s.sink.ID, s.F_mass-s.imass["Water"]])  # Exclude water

    # Collapse pass-through units if requested
    if collapse_units:
        links = collapse_passthrough_units(sys, links, limit)

    # labels = [u.ID for u in sys.units]
    labels = []
    original_labels = []  # Keep track of original IDs for mass flow lookup
    for l in links:
        if l[1] not in original_labels:
            original_labels.append(l[1])
        if l[2] not in original_labels:
            original_labels.append(l[2])

    # Create a dictionary to store mass flows for each stream
    stream_flows = {}
    for s in sys.streams:
        stream_flows[s.ID] = s.F_mass

    # Apply name mapping if provided, and add mass flows to labels
    if name_mapping:
        for orig_label in original_labels:
            mapped_name = name_mapping.get(orig_label, orig_label)
            # Add mass flow to stream labels (but not to unit labels)
            if orig_label in stream_flows and stream_flows[orig_label] > 0:
                # Check if it's RNG stream for special annotation
                if 'RNG' in orig_label and 'leak' not in orig_label.lower():
                    labels.append(f"{mapped_name}\n172 GJ/year")
                else:
                    labels.append(f"{mapped_name}\n{stream_flows[orig_label]:.0f} kg/hr")
            else:
                labels.append(mapped_name)

        # Update links with mapped names
        mapped_links = []
        for link in links:
            source_name = name_mapping.get(link[1], link[1])
            target_name = name_mapping.get(link[2], link[2])

            # Add mass flow to labels
            if link[1] in stream_flows and stream_flows[link[1]] > 0:
                if 'RNG' in link[1] and 'leak' not in link[1].lower():
                    source_name = f"{source_name}\n172 GJ/year"
                else:
                    source_name = f"{source_name}\n{stream_flows[link[1]]:.0f} kg/hr"

            if link[2] in stream_flows and stream_flows[link[2]] > 0:
                if 'RNG' in link[2] and 'leak' not in link[2].lower():
                    target_name = f"{target_name}\n172 GJ/year"
                else:
                    target_name = f"{target_name}\n{stream_flows[link[2]]:.0f} kg/hr"

            mapped_link = [
                link[0],  # Keep original ID
                source_name,  # Map source with flow
                target_name,  # Map target with flow
                link[3]   # Keep value
            ]
            mapped_links.append(mapped_link)
        links = mapped_links
    else:
        # No mapping provided, just use original labels with flows
        for orig_label in original_labels:
            if orig_label in stream_flows and stream_flows[orig_label] > 0:
                if 'RNG' in orig_label and 'leak' not in orig_label.lower():
                    labels.append(f"{orig_label}\n172 GJ/year")
                else:
                    labels.append(f"{orig_label}\n{stream_flows[orig_label]:.0f} kg/hr")
            else:
                labels.append(orig_label)

    sources = [labels.index(i[1]) for i in links]
    targets = [labels.index(i[2]) for i in links]
    values = [i[3] for i in links]

    # Create node colors - colorful scheme
    node_colors = []
    for label in labels:
        if ('RNG' in label and 'leak' not in label.lower()):
            node_colors.append('rgba(0, 123, 255, 0.9)')  # Bright Blue for RNG
        elif 'Biochar' in label or 'SoilAmendment' in label:
            node_colors.append('rgba(139, 69, 19, 0.9)')  # Brown for Biochar
        elif 'Feed' in label or 'SHW' in label or 'DW' in label or 'BM' in label:
            node_colors.append('rgba(34, 139, 34, 0.8)')  # Forest Green for feeds
        elif 'Biogas' in label or 'CH4' in label or 'Methane' in label:
            node_colors.append('rgba(255, 140, 0, 0.8)')  # Dark Orange for biogas
        elif 'MEA' in label:
            node_colors.append('rgba(138, 43, 226, 0.8)')  # Blue Violet for MEA
        elif 'CO2' in label or 'Flue' in label:
            node_colors.append('rgba(220, 20, 60, 0.8)')  # Crimson for CO2/emissions
        elif 'Digestate' in label or 'wastewater' in label.lower():
            node_colors.append('rgba(210, 105, 30, 0.7)')  # Chocolate for waste streams
        elif 'Digester' in label or 'Reactor' in label or 'Pyrolysis' in label:
            node_colors.append('rgba(70, 130, 180, 0.8)')  # Steel Blue for reactors
        elif 'Compressor' in label or 'Pump' in label:
            node_colors.append('rgba(100, 149, 237, 0.7)')  # Cornflower Blue for equipment
        elif 'Absorber' in label or 'Stripper' in label or 'Flash' in label:
            node_colors.append('rgba(147, 112, 219, 0.7)')  # Medium Purple for separation
        elif 'Dryer' in label or 'Cooler' in label or 'Heat' in label:
            node_colors.append('rgba(255, 99, 71, 0.7)')  # Tomato for heat exchange
        elif 'leak' in label.lower():
            node_colors.append('rgba(255, 0, 0, 0.8)')  # Red for leaks
        else:
            node_colors.append('rgba(128, 128, 128, 0.6)')  # Gray for others

    # Create link colors - colorful scheme matching flows
    link_colors = []
    for i, (src, tgt, v) in enumerate(zip(sources, targets, values)):
        alpha = 0.5 + 0.4*v / max(values)  # Variable transparency based on flow size

        if 'leak' in labels[src].lower() or 'leak' in labels[tgt].lower():
            link_colors.append(f"rgba(255, 0, 0, {alpha})")  # Red for leaks
        elif 'RNG' in labels[src] or 'RNG' in labels[tgt]:
            link_colors.append(f"rgba(0, 123, 255, {alpha})")  # Bright Blue for RNG
        elif 'Biochar' in labels[src] or 'Biochar' in labels[tgt] or 'SoilAmendment' in labels[src] or 'SoilAmendment' in labels[tgt]:
            link_colors.append(f"rgba(139, 69, 19, {alpha})")  # Brown for Biochar
        elif 'Feed' in labels[src] or 'Feed' in labels[tgt]:
            link_colors.append(f"rgba(34, 139, 34, {alpha})")  # Green for feeds
        elif 'Biogas' in labels[src] or 'Biogas' in labels[tgt] or 'CH4' in labels[src] or 'CH4' in labels[tgt]:
            link_colors.append(f"rgba(255, 140, 0, {alpha})")  # Orange for biogas
        elif 'MEA' in labels[src] or 'MEA' in labels[tgt]:
            link_colors.append(f"rgba(138, 43, 226, {alpha})")  # Purple for MEA
        elif 'CO2' in labels[src] or 'CO2' in labels[tgt] or 'Flue' in labels[src] or 'Flue' in labels[tgt]:
            link_colors.append(f"rgba(220, 20, 60, {alpha})")  # Crimson for CO2
        elif 'Digestate' in labels[src] or 'Digestate' in labels[tgt] or 'wastewater' in labels[src].lower() or 'wastewater' in labels[tgt].lower():
            link_colors.append(f"rgba(210, 105, 30, {alpha})")  # Chocolate for waste
        else:
            link_colors.append(f"rgba(100, 149, 237, {alpha})")  # Cornflower Blue for others

    # Optional: collapse chain nodes (disabled for better readability)
    # nodes, sources, targets, values = collapse_chain_nodes(labels, sources, targets, values)

    # create sankey diagram with improved styling - MORE COMPACT
    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',  # Better arrangement of nodes
        orientation='h',  # Horizontal orientation
        node = dict(
            pad = 25,  # Reduced spacing for more compact diagram
            thickness = 12,  # Thinner nodes for compactness
            line = dict(color = "black", width = 0.8),
            label = labels,
            color = node_colors
        ),
        link = dict(
            source = sources,
            target = targets,
            value = values,
            color = link_colors
        )
    )])
    fig.update_layout(
        title_text=f"{scenario}",
        font_size=10,  # Smaller font for compactness
        width=1600,  # Wider for horizontal layout
        height=900   # Taller for better visibility
    )

    # Save based on user preference
    if save_image and filename.endswith('.png'):
        try:
            fig.write_image(f"{filename}", scale=1, width=1200, height=800)
            print(f"✓ Saved image: {filename}")
        except Exception as e:
            print(f"⚠ Could not save PNG (missing kaleido/Chrome): {e}")
            html_filename = filename.replace('.png', '.html')
            fig.write_html(html_filename)
            print(f"✓ Saved HTML instead: {html_filename}")
    else:
        # Save as HTML (always works, no dependencies)
        if not filename.endswith('.html'):
            filename = filename.replace('.png', '.html')
        fig.write_html(filename)
        print(f"✓ Saved interactive HTML: {filename}")
# %%

def sankeys_energy(sys, scenario="", limit=0, filename="energy_balance_sankey_full.html", save_image=False, name_mapping=None, collapse_units=True):
    """
    Generate energy balance Sankey diagram.

    Parameters
    ----------
    sys : biosteam.System
        System to analyze
    scenario : str
        Scenario name for the title
    limit : float
        Minimum energy flow to include in diagram (kJ/hr)
    filename : str
        Output filename (html or png)
    save_image : bool
        If True, tries to save as PNG (requires kaleido/Chrome). If False, saves as HTML.
    name_mapping : dict, optional
        Dictionary to map stream/unit IDs to display names.
        Example: {'R1': 'Reactor', 'W_R1': 'Power to Reactor'}
    collapse_units : bool, optional
        If True, collapse units with no significant energy change (pass-through units)
    """
    links = []

    i = 0
    o = 0
    for s in sys.streams:
        if s.HHV < limit: continue
        if s.source == None: # input stream
            # links.append([s.ID, f"{i}", s.sink.ID, s.F_mass])
            links.append([s.ID, s.ID, s.sink.ID, s.HHV])
            i += 1
        elif s.sink == None:
            links.append([s.ID, s.source.ID, s.ID, s.HHV])
            o+=1
        else:
            links.append([s.ID, s.source.ID, s.sink.ID, s.HHV])

    for u in sys.units:
        try:
            if u.power_utility.rate*3600 > limit:
                links.append(["W_"+u.ID, "W_"+u.ID, u.ID, u.power_utility.rate*3600])
        except:
            pass

        try:
            if u.Hnet > limit:
                links.append(["Q_"+u.ID, u.ID, "Q_"+u.ID, -u.Hnet])
        except:
            pass

    # Collapse pass-through units if requested (for energy balance)
    if collapse_units:
        links = collapse_passthrough_units_energy(sys, links, limit)

    # labels = [u.ID for u in sys.units]
    labels = []
    original_labels = []
    for l in links:
        if l[1] not in original_labels:
            original_labels.append(l[1])
        if l[2] not in original_labels:
            original_labels.append(l[2])

    # Create a dictionary to store energy flows for each stream
    stream_energy = {}
    for s in sys.streams:
        stream_energy[s.ID] = s.HHV

    # Apply name mapping if provided, and add energy flows to labels
    if name_mapping:
        for orig_label in original_labels:
            mapped_name = name_mapping.get(orig_label, orig_label)
            # Add energy flow to stream labels
            if orig_label in stream_energy and stream_energy[orig_label] > 0:
                if 'RNG' in orig_label and 'leak' not in orig_label.lower():
                    labels.append(f"{mapped_name}\n172 GJ/year")
                else:
                    labels.append(f"{mapped_name}\n{stream_energy[orig_label]/1000:.0f} MJ/hr")
            elif orig_label.startswith('W_'):
                # Power utilities
                labels.append(f"{mapped_name}")
            elif orig_label.startswith('Q_'):
                # Heat utilities
                labels.append(f"{mapped_name}")
            else:
                labels.append(mapped_name)

        # Update links with mapped names
        mapped_links = []
        for link in links:
            source_name = name_mapping.get(link[1], link[1])
            target_name = name_mapping.get(link[2], link[2])

            # Add energy flow to labels
            if link[1] in stream_energy and stream_energy[link[1]] > 0:
                if 'RNG' in link[1] and 'leak' not in link[1].lower():
                    source_name = f"{source_name}\n172 GJ/year"
                else:
                    source_name = f"{source_name}\n{stream_energy[link[1]]/1000:.0f} MJ/hr"

            if link[2] in stream_energy and stream_energy[link[2]] > 0:
                if 'RNG' in link[2] and 'leak' not in link[2].lower():
                    target_name = f"{target_name}\n172 GJ/year"
                else:
                    target_name = f"{target_name}\n{stream_energy[link[2]]/1000:.0f} MJ/hr"

            mapped_link = [
                link[0],
                source_name,
                target_name,
                link[3]
            ]
            mapped_links.append(mapped_link)
        links = mapped_links
    else:
        # No mapping provided
        for orig_label in original_labels:
            if orig_label in stream_energy and stream_energy[orig_label] > 0:
                if 'RNG' in orig_label and 'leak' not in orig_label.lower():
                    labels.append(f"{orig_label}\n172 GJ/year")
                else:
                    labels.append(f"{orig_label}\n{stream_energy[orig_label]/1000:.0f} MJ/hr")
            else:
                labels.append(orig_label)

    sources = [labels.index(i[1]) for i in links]
    targets = [labels.index(i[2]) for i in links]
    values = [i[3] for i in links]

    # Optional: collapse chain nodes (disabled for better readability)
    # nodes, sources, targets, values = collapse_chain_nodes(labels, sources, targets, values)

    # Create node colors - highlight RNG and Biochar in dark blue, power in blue, heat in orange
    node_colors = []
    for label in labels:
        if ('RNG' in label and 'leak' not in label.lower()) or 'Biochar' in label or 'SoilAmendment' in label:
            node_colors.append('rgba(0, 51, 102, 0.9)')  # Dark Blue for RNG and Biochar
        elif 'W_' in label or 'Power' in label or 'Compres' in label:
            node_colors.append('rgba(30, 144, 255, 0.7)')  # Dodger Blue for power
        elif 'Q_' in label or 'Heat' in label or 'Cooling' in label:
            node_colors.append('rgba(255, 140, 0, 0.7)')  # Dark Orange for heat
        else:
            node_colors.append('rgba(100, 100, 100, 0.5)')  # Gray for others

    # Create link colors
    link_colors = []
    for i, (src, tgt, v) in enumerate(zip(sources, targets, values)):
        if ('RNG' in labels[src] or 'RNG' in labels[tgt] or
            'Biochar' in labels[src] or 'Biochar' in labels[tgt] or
            'SoilAmendment' in labels[src] or 'SoilAmendment' in labels[tgt]):
            if 'leak' not in labels[src].lower() and 'leak' not in labels[tgt].lower():
                alpha = 0.7*v / max(values)+0.3
                link_colors.append(f"rgba(0, 51, 102, {alpha})")  # Dark Blue for products
            else:
                alpha = 0.8*v / max(values)+0.2
                link_colors.append(f"rgba(255, 0, 0, {alpha})")  # Red for leaks
        elif 'W_' in labels[src] or 'Power' in labels[src]:
            alpha = 0.6*v / max(values)+0.3
            link_colors.append(f"rgba(30, 144, 255, {alpha})")  # Blue for power
        elif 'Q_' in labels[src] or 'Heat' in labels[src] or 'Cooling' in labels[src]:
            alpha = 0.6*v / max(values)+0.3
            link_colors.append(f"rgba(255, 140, 0, {alpha})")  # Orange for heat
        else:
            alpha = 0.8*v / max(values)+0.2
            link_colors.append(f"rgba(70, 130, 180, {alpha})")  # Steel Blue for others

    # create sankey diagram with improved styling - MORE COMPACT
    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',  # Better arrangement of nodes
        orientation='h',  # Horizontal orientation
        node = dict(
            pad = 25,  # Reduced spacing for more compact diagram
            thickness = 12,  # Thinner nodes for compactness
            line = dict(color = "black", width = 0.8),
            label = labels,
            color = node_colors
        ),
        link = dict(
            source = sources,
            target = targets,
            value = values,
            color = link_colors
        )
    )])
    fig.update_layout(
        title_text=scenario,
        font_size=10,  # Smaller font for compactness
        width=1600,  # Wider for horizontal layout
        height=900   # Taller for better visibility
    )

    # Save based on user preference
    if save_image and filename.endswith('.png'):
        try:
            fig.write_image(filename, scale=1, width=1200, height=800)
            print(f"✓ Saved image: {filename}")
        except Exception as e:
            print(f"⚠ Could not save PNG (missing kaleido/Chrome): {e}")
            html_filename = filename.replace('.png', '.html')
            fig.write_html(html_filename)
            print(f"✓ Saved HTML instead: {html_filename}")
    else:
        # Save as HTML (always works, no dependencies)
        if not filename.endswith('.html'):
            filename = filename.replace('.png', '.html')
        fig.write_html(filename)
        print(f"✓ Saved interactive HTML: {filename}")

    print(f"Energy Balance: {sum(values)} kJ/hr")
# %%

def collapse_chain_nodes(nodes, source, target, values):
    """
    Collapse nodes with only one incoming and one outgoing connection.
    Reimplemented without pandas dependency.
    """
    # Create list of connections
    connections = list(zip(source, target, values))

    # Count incoming and outgoing connections for each node
    all_nodes = set(source + target)
    incoming_count = {node: sum(1 for s, t, v in connections if t == node) for node in all_nodes}
    outgoing_count = {node: sum(1 for s, t, v in connections if s == node) for node in all_nodes}

    # Identify nodes with only one incoming and one outgoing connection
    single_pass_nodes = [
        node for node in all_nodes
        if incoming_count.get(node, 0) == 1 and outgoing_count.get(node, 0) == 1
    ]

    # Iterate over collapsible nodes and merge them
    for node in single_pass_nodes:
        # Find the single incoming and outgoing connections
        incoming = next((s, t, v) for s, t, v in connections if t == node)
        outgoing = next((s, t, v) for s, t, v in connections if s == node)

        # Create a new direct connection
        new_source = incoming[0]
        new_target = outgoing[1]
        new_value = min(incoming[2], outgoing[2])  # Preserve min flow

        # Remove old connections and add new one
        connections = [(s, t, v) for s, t, v in connections if s != node and t != node]
        connections.append((new_source, new_target, new_value))

    # Update source, target, and value lists
    new_source = [s for s, t, v in connections]
    new_target = [t for s, t, v in connections]
    new_values = [v for s, t, v in connections]

    # Update nodes list (remove collapsed nodes)
    new_nodes = [node for node in nodes if node not in single_pass_nodes]

    return new_nodes, new_source, new_target, new_values

##################### OLD CODE #####################

# # Energy Balance Sankey Diagram
# endUnits = [u.ID for u in system.flowsheet.unit["FiberDryer"].path_from(
#     system.flowsheet.unit["TFF1"], inclusive=True
# )] + ["FiberDryer"]
# units = [u for u in system.units[0:] if u.ID not in endUnits]
# links = []
# values = []
# colors = []
 
# for u in units:
#     try:
#         if u.power_utility.rate * 3600 / 1000 > 100:
#             links.append([
#                 f"W_{u.ID}: {u.power_utility.rate*3600/1000:.2f} MJ/hr",
#                 u.ID
#             ])
#             values.append(u.power_utility.rate*3600/1000)
#             # blue
#             colors.append("#1f77b4")
#     except:
#         pass
 
#     try:
#         if u.Hnet/1000 > 100:
#             links.append([
#                 f"Q_{u.ID}: {u.Hnet/1000:.2f} MJ/hr",
#                 u.ID
#             ])
#             values.append(u.Hnet/1000)
#             # orange
#             colors.append("#ff7f0e")
#     except:
#         pass
 
#     for i in u.ins:
#         if i.HHV/1000 > 100:
#             if i.source and i.source.ID in [u.ID for u in units]:
#                 try:
#                     links.append([
#                         f"{i.source.ID}",
#                         u.ID
#                     ])
#                     values.append(i.HHV / 1000)
#                     # light gray
#                     colors.append("#d1d1d1")
#                 except:
#                     pass
#             else:
#                 try:
#                     links.append([
#                         f"{i.ID}: {i.HHV/1000:.2f} MJ/hr",
#                         u.ID
#                     ])
#                     values.append(i.HHV/1000)
#                     # light gray
#                     colors.append("#d1d1d1")
#                 except:
#                     pass
 
# for o in system.products:
#     try:
#         if o.source.ID in [u.ID for u in units]:
#             print(o.source.ID, o.ID)
#             links.append([
#                 f"{o.source.ID}",
#                 f"{o.ID}: {o.HHV/1000:.2f} MJ/hr"
#             ])
#             values.append(o.HHV/1000)
#             colors.append("#d1d1d1")
#     except Exception as e:
#         print(f"Could not add {o.ID} to the Sankey diagram.", e)
 
# links.append([
#     "Centrifuge4",
#     f"Fiber: {system.flowsheet.unit['Centrifuge4'].outs[0].HHV/1000:.2f} MJ/hr"
# ])
# values.append(system.flowsheet.unit["Centrifuge4"].outs[0].HHV/1000)
# colors.append("#d1d1d1")
 
# node_labels = list(set([l[0] for l in links] + [l[1] for l in links]))
# source_nodes = [node_labels.index(l[0]) for l in links]
# target_nodes = [node_labels.index(l[1]) for l in links]
 
 
# # pads = [random.randint(15, 100) for _ in range(len(node_labels))]
 
# import random
# def get_color(node):
#     if "W_" in node:
#         return "#1f77b4"
#     elif "Q_" in node:
#         return "#ff7f0e"
#     else:
#         # return a random color for the rest
#         return "rgba(" + ",".join([str(random.randint(0, 255)) for _ in range(3)]) + ", 0.5)"
 
# node_colors = [get_color(node) for node in node_labels]
# fig = go.Figure(
#     go.Sankey(
#         arrangement="snap",
#         node=dict(
#             pad=200000,
#             thickness=10,
#             line=dict(color="black", width=0.5),
#             label=node_labels,
#             color=node_colors,
#             align="right",
#             # color="rgba(31, 119, 180, 0.5)"
#         ),
#         link=dict(
#             source=source_nodes,
#             target=target_nodes,
#             value=values,
#             # label= [v for v in values],
#             color=colors,
#         ),
#     )
# )
 
# fig.update_layout(
#     title_text="Energy Balance Sankey Diagram for Synthetic Spider Silk Process",
#     font_size=14,
#     width=72 * 15,
#     height=72 * 12,
# )
# fig.write_image("energy_balance_plotly.png")
# fig.show()
 
# # %%
# # %%
# # Mass Balance Sankey Diagram
# endUnits = [
#     u.ID
#     for u in system.flowsheet.unit["FiberDryer"].path_from(
#         system.flowsheet.unit["TFF1"], inclusive=True
#     )
# ] + ["FiberDryer"]
# units = [u for u in system.units[0:] if u.ID not in endUnits]
# links = []
# values = []
# colors = []
 
# for u in units:
#     for i in u.ins:
#         if i.F_mass > 1:
#             if i.source and i.source.ID in [u.ID for u in units]:
#                 try:
#                     links.append([f"{i.source.ID}", u.ID])
#                     values.append(i.F_mass)
#                     # light gray
#                     colors.append("#d1d1d1")
#                 except:
#                     pass
#             else:
#                 try:
#                     links.append([f"{i.ID}: {i.F_mass:.2f} kg/hr", u.ID])
#                     values.append(i.F_mass)
#                     # light gray
#                     colors.append("#d1d1d1")
#                 except:
#                     pass
 
# for o in system.products:
#     try:
#         if o.source.ID in [u.ID for u in units]:
#             print(o.source.ID, o.ID)
#             links.append([f"{o.source.ID}", f"{o.ID}: {o.F_mass:.2f} kg/hr"])
#             values.append(o.F_mass)
#             colors.append("#d1d1d1")
#     except Exception as e:
#         print(f"Could not add {o.ID} to the Sankey diagram.", e)
 
# links.append(
#     [
#         "Centrifuge4",
#         "Fiber: "
#         + f"{system.flowsheet.unit['Centrifuge4'].outs[0].F_mass:0.2f}"
#         + " kg/hr",
#     ]
# )
# values.append(system.flowsheet.unit["Centrifuge4"].outs[0].F_mass)
# colors.append("#d1d1d1")
 
# node_labels = list(set([l[0] for l in links] + [l[1] for l in links]))
# source_nodes = [node_labels.index(l[0]) for l in links]
# target_nodes = [node_labels.index(l[1]) for l in links]
 
 
# # pads = [random.randint(15, 100) for _ in range(len(node_labels))]
 
# import random
 
 
# def get_color(node):
#     if "W_" in node:
#         return "#1f77b4"
#     elif "Q_" in node:
#         return "#ff7f0e"
#     else:
#         # return a random color for the rest
#         return (
#             "rgba("
#             + ",".join([str(random.randint(0, 255)) for _ in range(3)])
#             + ", 0.5)"
#         )
 
 
# node_colors = [get_color(node) for node in node_labels]
# fig = go.Figure(
#     go.Sankey(
#         arrangement="snap",
#         node=dict(
#             pad=200,
#             thickness=10,
#             line=dict(color="black", width=0.5),
#             label=node_labels,
#             color=node_colors,
#             align="left",
#             # color="rgba(31, 119, 180, 0.5)"
#         ),
#         link=dict(
#             source=source_nodes,
#             target=target_nodes,
#             value=values,
#             # label= [v for v in values],
#             color=colors,
#         ),
#     )
# )
 
# fig.update_layout(
#     title_text="Mass Balance Sankey Diagram for Synthetic Spider Silk Process",
#     font_size=14,
#     width=72 * 15,
#     height=72 * 15,
# )
# fig.write_image("mass_balance_plotly.png")
# fig.show()
 
 
# # %%
# inChems = []
# for i in system.flowsheet.unit["Dialysis"].ins:
#     for c in i.chemicals:
#         if i.imass[c.ID] > 1:
#             print(c.ID,  i.imass[c.ID], c.HHV, c.HHV*i.imass[c.ID]/1000)
#             inChems.append([c.ID, i.imass[c.ID], c.HHV, c.HHV * i.imass[c.ID] / 1000])
 
# print("\nOuts")
# outs = []
# for o in system.flowsheet.unit["Dialysis"].outs:
#     for c in o.chemicals:
#         if o.imass[c.ID] > 1:
#             print(c.ID, o.imass[c.ID], c.HHV, c.HHV*o.imass[c.ID]/1000)
#             outs.append([c.ID, o.imass[c.ID], c.HHV, c.HHV*o.imass[c.ID]/1000])
# # %%
# sorted(inChems, key=lambda x: x[3], reverse=True)
# # %%
# sorted(outs, key=lambda x: x[3], reverse=True)
 
 
# %%
if __name__ == "__main__":
    # Base parameters for the system
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

    # Create and simulate the system
    system_base, tea_base, streams_base, _ = create_and_simulate_system(**base_params)

    # Generate mass balance Sankey diagram
    print("\nGenerating Mass Balance Sankey Diagram...")
    sankeys(system_base, scenario="Base Case Mass Balance Sankey Diagram",
            limit=0, filename="results/mass_balance_sankey_basecase.png")

    # Generate energy balance Sankey diagram
    print("\nGenerating Energy Balance Sankey Diagram...")
    sankeys_energy(system_base, scenario="Base Case Energy Balance Sankey Diagram",
                   limit=0, filename="results/energy_balance_sankey_basecase.html",
                   save_image=False)

    print("\n✓ Done! Diagrams generated successfully.")
    print("\nNote: To save as PNG instead of HTML, change SAVE_AS_PNG = True in the code")
    print("      (PNG export requires kaleido or Chrome to be installed)")
