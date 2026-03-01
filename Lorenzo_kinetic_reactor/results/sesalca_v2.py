# from numba.core.types import Any
"""
SESALCA Module

This module provides functionality to initialize and manage flow and embedding data.
It uses cosine similarity to search embeddings and integrates with OpenAI for additional features.

Dependencies:
- sklearn
- openai
- datetime
- pydantic
"""
#%%
import olca_ipc as ipc  # https://greendelta.github.io/openLCA-ApiDoc/examples/pyipc_from_scratch.html
import olca_schema as o 
import sys
import os
import json
# from functools import lru_cache
#%%
# _lca = ipc.Client("http://10.24.251.4:8080")
_lca = ipc.Client()
# search the embeddings using cosine similarity
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI  
from datetime import datetime
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

from pydantic import BaseModel
import biosteam as bst
#%%
_flows = {}
_embeddings = {}
_flow_embeddings = {}
descriptors = []

def get_processes(query, number=10):
    """
    Retrieve a list of processes based on the similarity of their embeddings to the given query.

    Args:
        query (str): The query string to search for similar processes.
        number (int, optional): The maximum number of similar processes to return. Defaults to 10.

    Returns:
        list: A list of process identifiers that are most similar to the query. If the query is empty or an error occurs, an empty list is returned.

    Raises:
        Exception: If there is an error during the process of retrieving or calculating embeddings.
    """
    if query == "":
        return []
    try:
        global _embeddings
        inEmbedding = client.embeddings.create(input=[query], model="text-embedding-3-small").data[0].embedding

        similarity_scores = []
        for (k, v) in _embeddings.items():
            similarity_scores.append([k, cosine_similarity([inEmbedding], [v])[0][0]])
        sorted_scores = [[k, v] for k, v in sorted(similarity_scores, key=lambda item: item[1], reverse=True)]
        processes = [x[0] for x in sorted_scores[0:number]]
        return processes
    except Exception as e:
        print("Error getting processes for: ", query, ". " + str(e))
        return []

def get_synonyms(query, n=5):
    """
    Get a list of synonyms for the given query using OpenAI's chat completions.
    
    Args:
        query (str): The query string to find synonyms for.
        n (int, optional): The number of synonyms to return. Defaults to 5.
    
    Returns:
        list: A list of synonyms for the query.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides british synonyms. Do not explain. Return only a list of synonyms, separated by commas."},
                {"role": "user", "content": f"Provide {n} synonyms for: {query}"}
            ]
        )
        synonyms = response.choices[0].message.content.split(", ")
        return synonyms[:n]
    except Exception as e:
        print("Error getting synonyms for: ", query, ". " + str(e))
        return []

def recommend_process(query, n=1, embeddings=False):
    """
    Recommend a process based on the given query.
    This function uses an external client to find and recommend processes that match the given query.
    It prefers market processes and those for the United States.
    Args:
        query (str): The query string to search for matching processes.
        n (int, optional): The number of processes to return. Defaults to 1.
    Returns:
        str or list: If n is 1, returns a single process name as a string. 
                     If n is greater than 1, returns a list of process names.
    Raises:
        Exception: If there is an error in recommending a process, it prints an error message and returns the query.
    """
    global descriptors
    try:
        _n = 20 if n < 20 else n
        if embeddings:
            processes = get_processes(query, _n)
        else:
            synonyms = [query] + get_synonyms(query, 5)
            processes = []
            if descriptors == []:
                descriptors = _lca.get_descriptors(o.Process)
            for s in synonyms:
                processes.extend([p.name for p in descriptors if p.name and s.lower() in p.name.lower()])
            processes = list(set(processes))
        
        process = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""
                
                I have found some processes that match your query: {'; '.join(processes)}"""},
                {"role": "user", "content": f"Which of these processes is the closest match to: {query}? Prefer market processes and those for the United States. Do not explain. Respond only with a process name that is in the list" }
            ]).choices[0].message.content

        if n == 1:
            for p in processes:
                if process in p:
                    return p
            return processes[0]
        elif len(processes) == 0:
            print("No processes found for: ", query, " try using ", ", ".join(synonyms))
            return query
        else:
            return processes[0:n]
    except Exception as e:
        print("Error recommending process for: ", query, ". " + str(e))
        return query

def describe_process(process):
    """
    Describes a given process by finding its reference and returning a formatted description.
    Args:
        process (str): The name or identifier of the process to describe.
    Returns:
        str: A formatted string containing the process name and description if the process is found.
        None: If the process is not found.
    Prints:
        "Process not found." if the process reference cannot be found.
    """
    process_ref = _lca.find(o.Process, process)
    if process_ref == None:
        print("Process not found.")
        return {
            "Name": process,
            "Description": "Process not found.",
            "Unit": ""
        }

    else:
        process = _lca.get(o.Process, process_ref.id)
        ref_unit = ""
        if process and process.exchanges:
            for e in process.exchanges:
                if e.is_quantitative_reference:
                    if e.flow and e.flow.ref_unit:
                        ref_unit = f"{e.amount} {e.flow.ref_unit}" 
                    break
        return {
            "Name": process.name if process and process.name else "Na",
            "Description": process.description if process and process.description else "No description available.",
            "Unit": ref_unit
        }

#@lru_cache(maxsize=10)
def get_product_system(process, location="US"):
    system_ref = _lca.find(o.ProductSystem, process)
    if system_ref != None:
        print("Product system already exists.")
        return system_ref
    
    system_ref = create_product_system(process)
    print("Product system created: ", system_ref)
    return system_ref

#@lru_cache(maxsize=10)
def get_method(method):
    methods = _lca.get_all(o.ImpactMethod)
    if len(methods) == 0:
        print("No methods found. Install the impact assessment methods in openLCA.")
        return None
    im = list(filter(lambda x: method in x.name, methods))
    if len(im) > 0:
        im = im[0]
    else:
        im = list(filter(lambda x: "TRACI" in x.name, methods))
        if len(im) > 0:
            im = im[0]
        else:
            im = methods[0]
            print("Method not found. Using default method: ", im.name)
    return im

def get_result(process, method):
    try:
        system_ref = get_product_system(process)
        if system_ref is None:
            print("Error getting product system in get_result. Returning None")
            return None
        im = get_method(method)

        system_ref.location = "US"

        if im:
            print("Using method: ", im.name)
        else:
            print("Method not found. Using default method: TRACI")
            im = get_method("TRACI")
        if im is None:
            print("No impact method found. Returning None")
            return None
        
        setup = o.CalculationSetup(
            target=o.Ref(
                ref_type=o.RefType.ProductSystem,
                id=system_ref.id,
                location="US"
            ),
            impact_method=im.to_ref(), # EF 3.1 Method (adapted)
            # nw_set=o.Ref(id="867fe119-0b5c-38a0-a3e6-1d845ffaedd5"),
        )

        result: ipc.Result = _lca.calculate(setup)
        result.wait_until_ready()
        print("Result ready: ", result)
        _lca.delete(system_ref)
        return result
    except Exception as ex:
        print("Error in get_result: ", ex)
        return None

def save_method_info(method_id):
    """Save method information to JSON file."""
    import os
    import json

    method_info_path = f"impact_data/method_{method_id[:8]}.json"

    # Check if file already exists
    if os.path.exists(method_info_path):
        print(f"✅ Method info already exists: {os.path.basename(method_info_path)}")
        return True

    try:
        method_obj = _lca.get(o.ImpactMethod, method_id)
        if method_obj is None:
            print(f"❌ Method not found: {method_id[:8]}...")
            return False

        method_info = {
            "method_id": method_id,
            "method_name": method_obj.name if hasattr(method_obj, 'name') else "Unknown Method",
            "created_at": datetime.now().isoformat(),
            "impact_categories": []
        }

        # Extract impact categories
        categories_count = 0
        if hasattr(method_obj, 'impact_categories') and method_obj.impact_categories:
            for category in method_obj.impact_categories:
                if category:
                    method_info["impact_categories"].append({
                        "id": category.id if hasattr(category, 'id') else '',
                        "name": category.name if hasattr(category, 'name') else '',
                        "ref_unit": category.ref_unit if hasattr(category, 'ref_unit') else ''
                    })
                    categories_count += 1

        os.makedirs("impact_data", exist_ok=True)
        with open(method_info_path, 'w') as f:
            json.dump(method_info, f, indent=2)

        print(f"💾 Method info saved: {os.path.basename(method_info_path)}")
        print(f"   📝 Method: {method_info['method_name']}")
        print(f"   🏷️  Categories: {categories_count}")

        return True

    except Exception as ex:
        print(f"❌ Error saving method info: {ex}")
        return False

def get_process_for_chemical(chemical_name):
    """
    Find a process that produces the given chemical by searching process names.
    This is useful for chemicals like 'Monoethanolamine' that might not have providers.

    Parameters:
    chemical_name (str): Name of the chemical to search for

    Returns:
    str: Name of the process that produces this chemical, or None if not found
    """
    try:
        # First try recommend_process which is more sophisticated
        recommended = recommend_process(chemical_name)
        if recommended and recommended != chemical_name:
            return recommended

        # If that doesn't work, search process names directly
        processes = _lca.get_descriptors(o.Process)

        # Look for processes that contain the chemical name
        for proc in processes:
            if proc.name and chemical_name.lower() in proc.name.lower():
                return proc.name

        return None
    except Exception as e:
        print(f"Error searching for chemical process: {e}")
        return None

def recalculate(process, _method="TRACI", return_json=False):
    """
    Force recalculation of impacts for a process, bypassing cache.

    Parameters:
    process (str): The name, ID, or description of the process.
    _method (str): The impact assessment method to use.
    return_json (bool): If True, returns structured JSON format.

    Returns:
    dict: Impact results in the specified format.
    """
    return get_total_impacts(process, _method, result=None, return_json=return_json, force_recalc=True)

#@lru_cache(maxsize=10)
def get_total_impacts(process, _method="TRACI", result=None, return_json=False, force_recalc=False):
    """
    Calculate the total environmental impacts for a given process using a specified impact assessment method.
    Uses JSON cache system to avoid recalculating existing results.

    Parameters:
    process (str): The name, ID, or description of the process for which to calculate impacts.
    _method (str, optional): The impact assessment method to use. Defaults to "TRACI".
    result (object, optional): Precomputed result object. If None, the result will be computed using the process and method. Defaults to None.
    return_json (bool, optional): If True, returns a structured JSON with metadata. Defaults to False.
    force_recalc (bool, optional): If True, bypasses cache and forces recalculation. Defaults to False.

    Returns:
    dict: Impact results in the specified format.
    """
    import os
    import json

    try:
        # Determine if input is process ID, process name, or flow description
        process_ref = None
        process_obj = None

        # First try to find by exact match (ID or name)
        process_ref = _lca.find(o.Process, process)

        # If it looks like a UUID/ID, try to get it directly
        if process_ref is None and len(process) > 30 and '-' in process:
            try:
                # First check if it's an elementary flow
                potential_flow = _lca.get(o.Flow, process)
                if potential_flow and hasattr(potential_flow, 'flow_type'):
                    if potential_flow.flow_type == o.FlowType.ELEMENTARY_FLOW:
                        print(f"🌍 Detected elementary flow: '{potential_flow.name}' (ID: {process[:8]}...)")
                        print(f"   Getting characterization factors instead of process impacts...")
                        elem_data = get_elementary_flow_characterization_factors(process, _method)

                        # Convert to format expected by get_total_impacts
                        if elem_data and not return_json:
                            results = elem_data.get('impacts', {}).copy()
                            results["Amount"] = elem_data.get('amount', 1.0)
                            results["Unit"] = elem_data.get('unit', 'kg')
                            results["Location"] = elem_data.get('location', '')
                            return results
                        else:
                            return elem_data

                # If not an elementary flow, try to get as process
                process_obj = _lca.get(o.Process, process)
                if process_obj:
                    print(f"Found process by direct ID: {process_obj.name}")
                    process_ref = process_obj.to_ref() if hasattr(process_obj, 'to_ref') else process_obj
            except:
                pass

        if process_ref is None:
            # If not found, treat it as a flow and use AI to find the best match
            print(f"Process '{process}' not found directly. Searching flows with AI recommendations...")

            try:
                # First get synonyms using OpenAI
                synonyms = get_synonyms(process, 10)  # Get more synonyms
                print(f"Generated synonyms: {synonyms}")

                # Search for flows using the original term + synonyms
                search_terms = [process] + synonyms
                matching_flows = []

                # Get flow descriptors if not already loaded
                global flow_descriptors
                if not flow_descriptors:
                    flow_descriptors = _lca.get_descriptors(o.Flow)

                # Search flows for each synonym - focus on product flows
                for term in search_terms:
                    term_lower = term.lower()
                    for flow_desc in flow_descriptors:
                        if flow_desc.name and term_lower in flow_desc.name.lower():
                            # Get the full flow to check its type
                            try:
                                full_flow = _lca.get(o.Flow, flow_desc.id)
                                # Add product flows, waste flows, and elementary flows
                                if (full_flow and hasattr(full_flow, 'flow_type') and
                                    (full_flow.flow_type == o.FlowType.PRODUCT_FLOW or
                                     full_flow.flow_type == o.FlowType.WASTE_FLOW or
                                     full_flow.flow_type == o.FlowType.ELEMENTARY_FLOW)):
                                    if flow_desc not in matching_flows:
                                        matching_flows.append(flow_desc)
                                elif full_flow and not hasattr(full_flow, 'flow_type'):
                                    # If no flow_type, assume it's a product flow (older databases)
                                    if flow_desc not in matching_flows:
                                        matching_flows.append(flow_desc)
                            except:
                                # If we can't get the full flow, skip it
                                continue

                if matching_flows:
                    print(f"Found {len(matching_flows)} potential product/waste/elementary flows")
                    # Show first few for debugging
                    for i, flow in enumerate(matching_flows[:3]):
                        try:
                            full_flow = _lca.get(o.Flow, flow.id)
                            flow_type = "UNKNOWN"
                            if hasattr(full_flow, 'flow_type'):
                                if full_flow.flow_type == o.FlowType.PRODUCT_FLOW:
                                    flow_type = "PRODUCT"
                                elif full_flow.flow_type == o.FlowType.WASTE_FLOW:
                                    flow_type = "WASTE"
                                elif full_flow.flow_type == o.FlowType.ELEMENTARY_FLOW:
                                    flow_type = "ELEMENTARY"
                            print(f"  {i+1}. {flow.name} (Type: {flow_type})")
                        except:
                            print(f"  {i+1}. {flow.name} (Type: ERROR)")
                    if len(matching_flows) > 3:
                        print(f"  ... and {len(matching_flows) - 3} more")

                    # Use OpenAI to select the best flow match
                    flow_names = [f.name for f in matching_flows[:20]]  # Limit to top 20
                    best_flow_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": f"You are helping to find the best flow match. Available flows: {'; '.join(flow_names)}"},
                            {"role": "user", "content": f"Which flow is the best match for '{process}'? Consider chemical names, synonyms, and common usage. Return only the exact flow name from the list."}
                        ]
                    ).choices[0].message.content.strip()

                    # Find the selected flow
                    selected_flow = None
                    for flow_desc in matching_flows:
                        if best_flow_response in flow_desc.name:
                            selected_flow = flow_desc
                            break

                    if not selected_flow and matching_flows:
                        selected_flow = matching_flows[0]  # Fallback to first match

                    if selected_flow:
                        print(f"AI selected best flow: {selected_flow.name}")
                        print(f"Flow ID: {selected_flow.id}")

                        # Get providers for this flow
                        try:
                            providers = _lca.get_providers(selected_flow.to_ref())
                            print(f"Found {len(providers) if providers else 0} providers for flow")

                            if providers and len(providers) > 0:
                                # If multiple providers, use AI to select the best one
                                if len(providers) > 1:
                                    provider_names = []
                                    for prov in providers[:10]:  # Limit to 10 providers
                                        if hasattr(prov, 'provider') and prov.provider:
                                            provider_names.append(prov.provider.name)
                                        elif hasattr(prov, 'name'):
                                            provider_names.append(prov.name)

                                    if provider_names:
                                        best_provider_response = client.chat.completions.create(
                                            model="gpt-4o-mini",
                                            messages=[
                                                {"role": "system", "content": f"Select the best provider for '{process}'. Available providers: {'; '.join(provider_names)}. Prefer market processes and those for the United States."},
                                                {"role": "user", "content": f"Which provider is best for '{process}'? Return only the exact provider name."}
                                            ]
                                        ).choices[0].message.content.strip()

                                        # Find the selected provider
                                        for prov in providers:
                                            prov_name = ""
                                            if hasattr(prov, 'provider') and prov.provider:
                                                prov_name = prov.provider.name
                                            elif hasattr(prov, 'name'):
                                                prov_name = prov.name

                                            if best_provider_response in prov_name:
                                                if hasattr(prov, 'provider'):
                                                    process_ref = prov.provider
                                                else:
                                                    process_ref = prov
                                                print(f"AI selected provider: {prov_name}")
                                                break

                                # If no AI selection worked, use first provider
                                if not process_ref:
                                    first_provider = providers[0]
                                    if hasattr(first_provider, 'provider'):
                                        process_ref = first_provider.provider
                                    else:
                                        process_ref = first_provider
                                    print(f"Using first provider: {process_ref.name if hasattr(process_ref, 'name') else 'Unknown'}")

                        except Exception as provider_error:
                            print(f"Error getting providers: {provider_error}")
                            providers = []

                        if not process_ref:
                            print(f"No providers found for selected flow: {selected_flow.name}")
                            return None
                    else:
                        print(f"No suitable flows found")
                        return None
                else:
                    print(f"No matching flows found for: {process}")
                    return None

            except Exception as e:
                print(f"Error in AI flow search: {e}")
                # Fallback to simple chemical process search
                chemical_process = get_process_for_chemical(process)
                if chemical_process:
                    print(f"Fallback: Found chemical process: {chemical_process}")
                    process_ref = _lca.find(o.Process, chemical_process)
                else:
                    return None

        # Get the full process object
        if process_ref:
            if not process_obj:  # If we don't already have it from direct ID lookup
                try:
                    if hasattr(process_ref, 'id'):
                        process_obj = _lca.get(o.Process, process_ref.id)
                    else:
                        process_obj = process_ref
                except:
                    process_obj = None

            # Extract name and ID safely
            if process_obj:
                process_name = process_obj.name if hasattr(process_obj, 'name') else str(process)
                process_id = process_obj.id if hasattr(process_obj, 'id') else str(process)
            else:
                process_name = process_ref.name if hasattr(process_ref, 'name') else str(process)
                process_id = process_ref.id if hasattr(process_ref, 'id') else str(process)

            # If we found it by direct ID, it's definitely a process
            if len(str(process)) > 30 and '-' in str(process):
                print(f"✅ Direct process ID match: {process_name}")
        else:
            return None

        # Check cache first (unless force_recalc is True)
        method_id_short = _method[:8] if _method and len(_method) >= 8 else (_method if _method else "TRACI")
        process_id_short = process_id[:8] if process_id and len(process_id) >= 8 else (process_id if process_id else "unknown")
        cache_file = f"impact_data/{process_id_short}_{method_id_short}.json"

        if not force_recalc and os.path.exists(cache_file):
            try:
                print(f"Checking cache file: {cache_file}")
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)

                # Check if method matches
                if cached_data.get('method_id') == _method:
                    print(f"✅ Using cached results for {process_name}")

                    if return_json:
                        return cached_data
                    else:
                        # Convert JSON format to traditional format
                        results = {}
                        impacts = cached_data.get('impacts', {})
                        if isinstance(impacts, dict):
                            for name, value in impacts.items():
                                results[name] = value
                        results["Amount"] = cached_data.get('amount', 0)
                        results["Unit"] = cached_data.get('unit', '')
                        results["Location"] = cached_data.get('location', '')
                        return results
                else:
                    print(f"🔄 Method changed from {cached_data.get('method_id')} to {_method}, recalculating...")
                    # Remove old cache file
                    os.remove(cache_file)
            except Exception as e:
                print(f"❌ Error reading cache: {e}")
                # Remove corrupted cache file
                try:
                    os.remove(cache_file)
                except:
                    pass

        # Ensure method info is cached before calculating
        try:
            method_obj = get_method(_method)
            if method_obj and hasattr(method_obj, 'id'):
                save_method_info(method_obj.id)
                print(f"📋 Method info cached for: {_method}")
        except Exception as method_error:
            print(f"Warning: Could not cache method info: {method_error}")

        # Calculate impacts if not cached or force_recalc
        if result is None:
            result = get_result(process_name, _method)
            if result is None:
                print("Error getting result. Returning zero impacts")
                method = get_method(_method)
                if method is None:
                    method = _lca.get_all(o.ImpactMethod)[0]
                categories = _lca.get(o.ImpactMethod, method.id)
                if categories is None or not hasattr(categories, 'impact_categories') or categories.impact_categories is None:
                    print("No impact categories found. Returning zero impacts")
                    return {}
                else:
                    zero_impacts = {f"{i.name}": 0 for i in categories.impact_categories}
                    if return_json:
                        result_data = {
                            "process_id": process_id,
                            "process_name": process_name,
                            "method_id": _method,
                            "method_name": method.name if method else "Unknown Method",
                            "calculated_at": datetime.now().isoformat(),
                            "amount": 0,
                            "unit": "",
                            "location": process_obj.location if process_obj and process_obj.location else "",
                            "impacts": zero_impacts
                        }
                        # Save to cache
                        os.makedirs("impact_data", exist_ok=True)
                        with open(cache_file, 'w') as f:
                            json.dump(result_data, f, indent=2)
                        return result_data
                    else:
                        return zero_impacts

        print(f"Getting total impacts for {process_name}")
        impacts = result.get_total_impacts()
        impact_dict = {}

        for impact in impacts:
            if impact.impact_category is not None:
                impact_dict[impact.impact_category.name] = impact.amount

        demand = result.get_demand()
        amount = demand.amount if demand else 0
        unit = ""
        location = ""

        if demand is not None:
            if demand.tech_flow is not None and demand.tech_flow.flow is not None:
                unit = demand.tech_flow.flow.ref_unit if hasattr(demand.tech_flow.flow, 'ref_unit') else ""
            location = demand.tech_flow.provider.location if demand.tech_flow is not None and demand.tech_flow.provider is not None else ""

        result.dispose()

        # Create result data
        method = get_method(_method)
        result_data = {
            "process_id": process_id,
            "process_name": process_name,
            "method_id": _method,
            "method_name": method.name if method else "Unknown Method",
            "calculated_at": datetime.now().isoformat(),
            "amount": amount,
            "unit": unit,
            "location": location,
            "impacts": impact_dict
        }

        # Save to cache
        try:
            os.makedirs("impact_data", exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump(result_data, f, indent=2)
            print(f"💾 Cached results to: {cache_file}")

            # Save method info separately (don't let this block caching)
            try:
                method_obj = get_method(_method)
                if method_obj and hasattr(method_obj, 'id'):
                    save_method_info(method_obj.id)
            except Exception as method_error:
                print(f"Warning: Could not save method info: {method_error}")
        except Exception as cache_error:
            print(f"Warning: Could not save cache: {cache_error}")

        if return_json:
            return result_data
        else:
            # Convert to traditional format
            results = impact_dict.copy()
            results["Amount"] = amount
            results["Unit"] = unit
            results["Location"] = location
            return results

    except ConnectionRefusedError as e:
        print(f"❌ Error de conexión: No se pudo conectar al servidor openLCA en localhost:8080")
        print(f"   Asegúrate de que openLCA esté ejecutándose y el servidor IPC esté activo")
        delete_product_system(process)
        return None
    except ConnectionError as e:
        print(f"❌ Error de conexión HTTP: {type(e).__name__}")
        print(f"   No se pudo establecer conexión con el servidor openLCA")
        print(f"   Verifica que openLCA esté ejecutándose y el servidor IPC esté activo en localhost:8080")
        delete_product_system(process)
        return None
    except Exception as ex:
        error_msg = str(ex)
        if "Connection refused" in error_msg or "Max retries exceeded" in error_msg:
            print(f"❌ Error de conexión: No se pudo conectar al servidor openLCA")
            print(f"   Detalles: {error_msg}")
            print(f"   Asegúrate de que openLCA esté ejecutándose y el servidor IPC esté activo")
        else:
            print("Error getting total impacts: ", ex)
        delete_product_system(process)
        return None

def delete_product_system(process):
    return
    print(f"Deleting product system for {process}")
    ps = _lca.get_all(o.ProductSystem)
    for p in ps:
        if p.name and process in p.name:
            print("Found product system: ", p)
            _lca.delete(p)
            print(f"Deleted product system for {process}")
            return True 
    print(f"Product system for {process} not found.")
    return False
# %%
#@lru_cache(maxsize=10)
def get_flow_impacts_of_process(process, result=None, method=None):
    """
    Get the flow impacts of a given process.

    This function calculates the flow impacts of a specified process by 
    retrieving the total impacts and then extracting the flow impacts for 
    each impact category.

    Parameters:
    process (object): The process for which to calculate flow impacts.
    result (object, optional): The result object containing impact data. 
                               If None, the result will be obtained using 
                               the specified method. Default is None.
    method (str, optional): The method to use for obtaining the result if 
                            result is None. Default is "TRACI".

    Returns:
    list: A list of dictionaries, each containing the following keys:
        - "Flow ID": The ID of the flow.
        - "Impact Category": The name of the impact category.
        - "Flow": The name of the flow.
        - "Category": The category of the flow.
        - "Amount": The amount of the flow impact.
        - "Unit": The unit of the flow impact.
    """
    if result == None:
        if method == None:
            method = "TRACI"
        result = get_result(process, method)
        if result == None:
            return {}
    impacts = result.get_total_impacts()
    flow_impacts = []
    for i in impacts:
        flows = result.get_flow_impacts_of(i.impact_category)
        for f in flows:

            flow_impacts.append({
                "Flow ID": f.envi_flow.flow.id,
                "Impact Category": i.impact_category.name,
                "Flow": f.envi_flow.flow.name,
                "Category": f.envi_flow.flow.category,
                "Amount": f.amount,
                "Unit": f.envi_flow.flow.ref_unit,
            })
    result.dispose()
    return flow_impacts

# %%
#@lru_cache(maxsize=10)
def get_tech_flow_impacts(process, result=None, method=None):
    if result == None:
        if method == None:
            method = "TRACI"
        result = get_result(process, method)
        if result == None:
            return {}
    techFlows = result.get_tech_flows()
    techFlowImpacts = []
    for f in techFlows[0:]:
        impacts = result.get_direct_impacts_of(f)
        for i in impacts:
            techFlowImpacts.append({
                "Flow ID": f.flow.id,
                "Flow Type": "tech flow",
                "Flow": f.flow.name,
                "process": f.provider.name,
                "Category": f.flow.category,
                "Impact Category": i.impact_category.name,
                "Amount": i.amount,
                "Unit": i.impact_category.ref_unit
            })
    result.dispose()
    return techFlowImpacts 

#%%
#@lru_cache(maxsize=10)
def get_direct_flow_impacts(process, method=None, force_recalc=False):
    """
    Get direct impacts for a process. Simple approach with caching.

    Parameters:
    process (str): Process ID or name
    method (str): LCA method (default: "TRACI")
    force_recalc (bool): Force recalculation bypassing cache

    Returns:
    dict: Process impact results
    """
    import os
    import json

    if method is None:
        method = "TRACI"

    # First, try to get cache data before server connection
    process_id = process  # Use process as initial ID

    # Check cache FIRST (before attempting any server connection)
    method_short = method[:8] if len(method) >= 8 else method
    process_id_short = process_id[:8] if len(process_id) >= 8 else process_id
    cache_file = f"impact_data/{process_id_short}_{method_short}_direct.json"

    if not force_recalc and os.path.exists(cache_file):
        try:
            print(f"📋 Checking cache: {cache_file}")
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            if cached_data.get('method') == method:
                print(f"✅ Using cached results for process {process_id_short}")
                return cached_data
            else:
                print(f"🔄 Method changed, recalculating...")
                os.remove(cache_file)
        except Exception as e:
            print(f"❌ Error reading cache: {e}")
            try:
                os.remove(cache_file)
            except:
                pass

    # Only attempt server connection if cache miss or force_recalc
    print(f"🔄 Cache miss or force recalc, attempting server connection...")

    # Verify it's a process
    process_obj = None
    process_id = None

    try:
        # If it looks like a UUID, try direct lookup
        if len(str(process)) > 30 and '-' in str(process):
            # First check if it's an elementary flow
            try:
                potential_flow = _lca.get(o.Flow, process)
                if potential_flow and hasattr(potential_flow, 'flow_type'):
                    if potential_flow.flow_type == o.FlowType.ELEMENTARY_FLOW:
                        print(f"🌍 Detected elementary flow: '{potential_flow.name}' (ID: {process[:8]}...)")
                        print(f"   Getting characterization factors instead of process impacts...")
                        return get_elementary_flow_characterization_factors(process, method)
            except:
                pass  # Not a flow, continue checking if it's a process

            process_obj = _lca.get(o.Process, process)
            process_id = process
            if process_obj:
                print(f"✅ Confirmed process ID: {process_obj.name}")
            else:
                print("❌ ID provided is not a valid process or flow")
                return None
        else:
            # Try lookup by name first
            process_ref = _lca.find(o.Process, process)
            if process_ref:
                process_obj = _lca.get(o.Process, process_ref.id)
                process_id = process_ref.id
                print(f"✅ Found process: {process_obj.name}")
            else:
                # Process not found directly, use AI flow search like in get_total_impacts
                print(f"🔍 Process '{process}' not found. Searching flows with AI...")

                try:
                    # Get synonyms with OpenAI
                    synonyms = get_synonyms(process, 10)
                    print(f"🤖 Generated synonyms: {synonyms}")

                    # Search for flows using original term + synonyms
                    search_terms = [process] + synonyms
                    matching_flows = []

                    # Get flow descriptors
                    global flow_descriptors
                    if not flow_descriptors:
                        flow_descriptors = _lca.get_descriptors(o.Flow)

                    # Search flows for each synonym - focus on product flows
                    for term in search_terms:
                        term_lower = term.lower()
                        for flow_desc in flow_descriptors:
                            if flow_desc.name and term_lower in flow_desc.name.lower():
                                try:
                                    full_flow = _lca.get(o.Flow, flow_desc.id)
                                    # Add product flows, waste flows, and elementary flows
                                    if (full_flow and hasattr(full_flow, 'flow_type') and
                                        (full_flow.flow_type == o.FlowType.PRODUCT_FLOW or
                                         full_flow.flow_type == o.FlowType.WASTE_FLOW or
                                         full_flow.flow_type == o.FlowType.ELEMENTARY_FLOW)):
                                        if flow_desc not in matching_flows:
                                            matching_flows.append(flow_desc)
                                    elif full_flow and not hasattr(full_flow, 'flow_type'):
                                        # Assume product/waste flow if no flow_type (older databases)
                                        if flow_desc not in matching_flows:
                                            matching_flows.append(flow_desc)
                                except:
                                    continue

                    if matching_flows:
                        print(f"🔍 Found {len(matching_flows)} potential product/waste/elementary flows")

                        # Use OpenAI to select best flow
                        flow_names = [f.name for f in matching_flows[:20]]
                        best_flow_response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": f"Available flows: {'; '.join(flow_names)}"},
                                {"role": "user", "content": f"Which flow best matches '{process}'? Return only the exact flow name."}
                            ]
                        ).choices[0].message.content.strip()

                        # Find selected flow
                        selected_flow = None
                        for flow_desc in matching_flows:
                            if best_flow_response in flow_desc.name:
                                selected_flow = flow_desc
                                break

                        if not selected_flow and matching_flows:
                            selected_flow = matching_flows[0]

                        if selected_flow:
                            print(f"🤖 AI selected flow: {selected_flow.name}")

                            # Get providers for this flow
                            providers = _lca.get_providers(selected_flow.to_ref())
                            print(f"🔍 Found {len(providers) if providers else 0} providers")

                            if providers and len(providers) > 0:
                                # Select best provider with AI if multiple
                                if len(providers) > 1:
                                    provider_names = []
                                    for prov in providers[:10]:
                                        if hasattr(prov, 'provider') and prov.provider:
                                            provider_names.append(prov.provider.name)

                                    if provider_names:
                                        best_provider_response = client.chat.completions.create(
                                            model="gpt-4o-mini",
                                            messages=[
                                                {"role": "system", "content": f"Providers: {'; '.join(provider_names)}. Prefer market processes and US."},
                                                {"role": "user", "content": f"Best provider for '{process}'? Return exact name."}
                                            ]
                                        ).choices[0].message.content.strip()

                                        # Find selected provider
                                        for prov in providers:
                                            if hasattr(prov, 'provider') and prov.provider:
                                                if best_provider_response in prov.provider.name:
                                                    process_ref = prov.provider
                                                    print(f"🤖 AI selected provider: {prov.provider.name}")
                                                    break

                                # Use first provider if no AI selection
                                if not process_ref:
                                    first_provider = providers[0]
                                    if hasattr(first_provider, 'provider'):
                                        process_ref = first_provider.provider
                                    else:
                                        process_ref = first_provider
                                    print(f"✅ Using first provider")

                                if process_ref:
                                    process_obj = _lca.get(o.Process, process_ref.id)
                                    process_id = process_ref.id
                                    print(f"✅ Found process via flow: {process_obj.name}")

                        if not process_ref:
                            print("❌ No suitable providers found")
                            return None
                    else:
                        print("❌ No matching flows found")
                        return None

                except Exception as e:
                    print(f"❌ Error in AI flow search: {e}")
                    return None

    except ConnectionRefusedError as e:
        print(f"❌ Error de conexión: No se pudo conectar al servidor openLCA en localhost:8080")
        print(f"   Asegúrate de que openLCA esté ejecutándose y el servidor IPC esté activo")
        return None
    except ConnectionError as e:
        print(f"❌ Error de conexión HTTP: {type(e).__name__}")
        print(f"   No se pudo establecer conexión con el servidor openLCA")
        print(f"   Verifica que openLCA esté ejecutándose y el servidor IPC esté activo en localhost:8080")
        return None
    except Exception as e:
        error_msg = str(e)
        if "Connection refused" in error_msg or "Max retries exceeded" in error_msg:
            print(f"❌ Error de conexión: No se pudo conectar al servidor openLCA")
            print(f"   Detalles: {error_msg}")
            print(f"   Asegúrate de que openLCA esté ejecutándose y el servidor IPC esté activo")
        else:
            print(f"❌ Error finding process: {e}")
            print(f"❌ Could not get impacts for process {process}")
        return None

    # Ensure method info is cached
    try:
        method_obj = get_method(method)
        if method_obj and hasattr(method_obj, 'id'):
            save_method_info(method_obj.id)
            print(f"📋 Method info cached for: {method}")
    except Exception as method_error:
        print(f"Warning: Could not cache method info: {method_error}")

    # Calculate impacts directly
    print(f"🔄 Calculating impacts for {process_obj.name}")

    try:
        # Create product system and calculate
        result = get_result(process_obj.name, method)
        if result is None:
            print("❌ Error getting result")
            return None

        # Get total impacts
        impacts = result.get_total_impacts()
        impact_dict = {}

        for impact in impacts:
            if impact.impact_category is not None:
                impact_dict[impact.impact_category.name] = impact.amount

        # Get demand information for amount, unit, location
        demand = result.get_demand()
        amount = demand.amount if demand else 1.0
        unit = ""
        location = ""

        if demand is not None:
            if demand.tech_flow is not None and demand.tech_flow.flow is not None:
                unit = demand.tech_flow.flow.ref_unit if hasattr(demand.tech_flow.flow, 'ref_unit') else ""
            if demand.tech_flow is not None and demand.tech_flow.provider is not None:
                location = demand.tech_flow.provider.location if hasattr(demand.tech_flow.provider, 'location') else ""

        result.dispose()

        # Save to cache
        try:
            cache_data = {
                "process_id": process_id,
                "process_name": process_obj.name,
                "method": method,
                "calculated_at": datetime.now().isoformat(),
                "amount": amount,
                "unit": unit,
                "location": location,
                "impacts": impact_dict
            }

            os.makedirs("impact_data", exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"💾 Cached results to: {cache_file}")

        except Exception as cache_error:
            print(f"Warning: Could not save cache: {cache_error}")

        return cache_data

    except Exception as ex:
        print(f"❌ Error calculating impacts: {ex}")
        return None

def recalculate_flow_impacts(process, method="TRACI"):
    """
    Force recalculation of direct flow impacts for a process, bypassing cache.

    Parameters:
    process (str): Process name or UUID
    method (str): LCA method (default: "TRACI")

    Returns:
    dict: Flow impacts data
    """
    return get_direct_flow_impacts(process, method, force_recalc=True)

def get_elementary_flow_characterization_factors(flow_id, method_id=None):
    """
    Get characterization factors for an elementary flow from a specific impact method.

    Elementary flows (like CH4, CO2) have characterization factors that define their
    impact per unit of emission. This function retrieves those factors.

    Parameters:
    flow_id (str): UUID of the elementary flow
    method_id (str): UUID of the impact method (default: TRACI)

    Returns:
    dict: Characterization factors by impact category
        {
            'process_id': flow_id,
            'process_name': flow_name,
            'method_id': method_id,
            'method_name': method_name,
            'amount': 1.0,
            'unit': flow_unit,
            'impacts': {
                'Global warming': 25.0,  # kg CO2 eq per kg CH4
                ...
            }
        }
    """
    import os
    import json

    if method_id is None:
        method_id = "d2c781ce-21b4-3218-8fca-78133f2c8d4d"  # TRACI by default

    try:
        # Get the flow object
        flow_obj = _lca.get(o.Flow, flow_id)
        if not flow_obj:
            print(f"❌ Flow not found: {flow_id}")
            return None

        # Check if it's an elementary flow
        if hasattr(flow_obj, 'flow_type') and flow_obj.flow_type != o.FlowType.ELEMENTARY_FLOW:
            print(f"⚠️ Warning: {flow_obj.name} is not an elementary flow")
            return None

        print(f"🌍 Getting characterization factors for elementary flow: {flow_obj.name}")
        print(f"   Flow ID: {flow_id[:8]}...")

        # Get the impact method
        method_obj = _lca.get(o.ImpactMethod, method_id)
        if not method_obj:
            print(f"❌ Method not found: {method_id}")
            return None

        print(f"📊 Using method: {method_obj.name}")

        # Extract characterization factors from impact categories
        impact_factors = {}

        if hasattr(method_obj, 'impact_categories') and method_obj.impact_categories:
            for category_ref in method_obj.impact_categories:
                # Get full category
                category = _lca.get(o.ImpactCategory, category_ref.id)

                if category and hasattr(category, 'impact_factors') and category.impact_factors:
                    # Look for this flow in the impact factors
                    for factor in category.impact_factors:
                        if hasattr(factor, 'flow') and factor.flow and factor.flow.id == flow_id:
                            factor_value = factor.value if hasattr(factor, 'value') else 0.0
                            impact_factors[category.name] = factor_value
                            print(f"   ✓ {category.name}: {factor_value:.4e} {category.ref_unit}/kg")
                            break

        if not impact_factors:
            print(f"⚠️ No characterization factors found for {flow_obj.name}")
            print(f"   This flow may not be characterized in the {method_obj.name} method")
            # Return zeros for all categories
            if hasattr(method_obj, 'impact_categories'):
                for category_ref in method_obj.impact_categories:
                    category = _lca.get(o.ImpactCategory, category_ref.id)
                    if category:
                        impact_factors[category.name] = 0.0

        # Get flow unit
        flow_unit = "kg"
        if hasattr(flow_obj, 'flow_properties') and flow_obj.flow_properties:
            for prop in flow_obj.flow_properties:
                if hasattr(prop, 'reference_flow_property') and prop.reference_flow_property:
                    if hasattr(prop, 'flow_property') and prop.flow_property:
                        fp = _lca.get(o.FlowProperty, prop.flow_property.id)
                        if fp and hasattr(fp, 'unit_group') and fp.unit_group:
                            ug = _lca.get(o.UnitGroup, fp.unit_group.id)
                            if ug and hasattr(ug, 'reference_unit'):
                                flow_unit = ug.reference_unit
                            break

        # Build result
        result_data = {
            "process_id": flow_id,
            "process_name": flow_obj.name,
            "method_id": method_id,
            "method_name": method_obj.name if method_obj else "Unknown Method",
            "calculated_at": datetime.now().isoformat(),
            "amount": 1.0,
            "unit": flow_unit,
            "location": "",
            "impacts": impact_factors,
            "is_elementary_flow": True
        }

        # Cache the result
        try:
            cache_file = f"impact_data/{flow_id[:8]}_{method_id[:8]}_elementary.json"
            os.makedirs("impact_data", exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump(result_data, f, indent=2)
            print(f"💾 Cached elementary flow CFs to: {cache_file}")
        except Exception as cache_error:
            print(f"⚠️ Could not cache: {cache_error}")

        return result_data

    except Exception as e:
        print(f"❌ Error getting characterization factors: {e}")
        return None

#%%
def create_product_system(process):
    system_ref = _lca.find(o.ProductSystem, process)
    if system_ref is not None:
        print("Product system already exists. Deleting it first.")
        _lca.delete(system_ref)
    

    processes = [p for p in _lca.get_descriptors(o.Process) if process in p.name]
    id = None
    for p in processes:
        if p.location == "US":
            print("Found US process: ", p)
            id = p.id
            break

    if id is None:
        print("US process not found. Using Global, or RoW, or ReR process.")
        for p in processes:
            if p.location == "GLO":
                print("Found Global process: ", p)
                id = p.id
                break
            elif p.location == "RoW":
                print("Found RoW process: ", p)
                id = p.id
                break
            elif p.location == "ReR":
                print("Found ReR process: ", p)
                id = p.id
                break
            elif p.location == "CN":
                print("Found China process: ", p)
                id = p.id
                break
    if id is None:        
        id = processes[0].id
        print("Using first process found: ", processes[0])

    process_ref = _lca.get(o.Process, id)
    if process_ref is None:
        print("Process not found.")
        return None
    
    config = o.LinkingConfig(
        prefer_unit_processes=False,
        provider_linking=o.ProviderLinking.PREFER_DEFAULTS,
    )
    system_ref = _lca.create_product_system(process_ref, config)
    if system_ref is None:
        print("Error creating product system.")
        return None
    system_ref.location = process_ref.location if process and process_ref.location else "US"
    return system_ref

def delete_process(name):
    process = _lca.find(o.Process, name)
    if process == None:
        print("Process not found.")
        return None
    _lca.delete(process)
    return process

#%%
def find_flows(name):
    global _flows
    matches = []
    matches = list(filter(lambda x: name.lower() in x.name.lower(), _flows.keys()))
    return matches

def find_providers(flow):
    providers = []
    for p in _lca.get_providers(flow):
        providers.append(p)
    return providers

#%%
#%%
# %%
flow_descriptors = []
def recommend_flow(query, n=1):
    global _flow_embeddings

    synonyms = get_synonyms(query, 5)
    flows = []
    flow_descriptors = _lca.get_descriptors(o.Flow)
    
    for s in synonyms:
        flows.extend([f.name for f in flow_descriptors if f.name and s.lower() in f.name.lower()])

    flow2 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""
             
             I have found some flows that match your query: {'; '.join(flows)}"""},
            {"role": "user", "content": f"Which of these flows is the closest match to: {query}? Provide only the flow. Do not explain" }
        ]).choices[0].message.content
    
    if n == 1:
        for f in flows:
            if flow2 in f:
                return f
    else:
        return flows[0:n]
    
    if len(flows) == 0:
        print("No flows found for: ", query)
        return None
    else:
        return flows[0]
# %%
def create_process(name, flows, overwrite=False):
    """
    flows should include:
    {
        "Name": "Water",
        "Amount": 100,
        "Unit": "m3",
        "Reference": False,
        "Type": "Input",
        "Provider": None
    }
    """

    # Delete product system first
    product_system = _lca.find(o.ProductSystem, name)
    if product_system != None:
        print("Product system already exists. Deleting it first.")
        _lca.delete(product_system)

    process = _lca.find(o.Process, name)
    if process != None and not overwrite:
        print("Process already exists. Delete it first.")
        return process
    else:
        if process != None and overwrite:
            print("Process already exists. Deleting it first.")
            _lca.delete(process)
    process = o.new_process(name)

    for f in flows:
        p = f["Provider"]
        if p != None and p != "":
            provider = _lca.find(o.Process, name=p)
        else:
            provider = None

        if provider == None:
            print("Provider not found: ", p)
            
            rf = _lca.get(o.Flow, name=f["Name"])
            if rf is None:
                print("Flow not found: ", f["Name"])
                group = [u for u in _lca.get_descriptors(o.UnitGroup) if u.name and "Sesalca units " + f["Unit"] in u.name]
                if len(group) == 0:
                    group = o.new_unit_group("Sesalca units " + f["Unit"], f["Unit"])
                    group.last_change =  datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%zZ')
                    print("New group: ", group)
                    _lca.put(group)
                else:
                    group = _lca.get(o.UnitGroup, group[0].id)
                unit = _lca.get(o.FlowProperty, name=f["Unit"])
                if unit is None and group is not None:
                    unit = o.new_flow_property(f["Unit"], group.to_ref())
                    unit.last_change =  datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%zZ')
                    print("New unit: ", unit)
                    _lca.put(unit)

                if f["Type"] == "Waste":
                    rf = o.new_waste(f["Name"], unit)
                else:
                    rf = o.new_product(f["Name"], unit)
                rf.last_change =  datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%zZ')

                # print("New flow: ", _lca.put(rf))
                _lca.put(rf)
            else: 
                print("Flow found: ", f["Name"], rf.to_dict())
        else:
            provider = _lca.get(o.Process, provider.id)
            rf = None 
            if provider and provider.exchanges is not None:
                for e in provider.exchanges:
                    if e.is_quantitative_reference:
                        rf = e.flow
                        break

        if f["Type"] == "Input" and rf:
            qref = o.new_input(process, rf, f["Amount"])
        elif f["Type"] == "Output" and rf:
            qref = o.new_output(process, rf, f["Amount"])
        elif f["Type"] == "Product" and rf:
            qref = o.new_output(process, rf, f["Amount"])
        elif f["Type"] == "Waste" and rf:
            qref = o.new_output(process, rf, f["Amount"])
        else:
            if rf:
                qref = o.new_input(process, rf, f["Amount"])

        if f["Reference"]:
            qref.is_quantitative_reference = True

        if f.get("Avoided", False):
            qref.is_avoided_product = True

        if f["Provider"] != None and f["Provider"] != "":
            provider = _lca.find(o.Process, name=f["Provider"])
            if provider != None:
                qref.default_provider = provider.to_ref()
                f["Provider"] = provider.name
            else:
                print("Provider not found: ", f["Provider"], ". Using default provider.")

    process.last_change =  datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%zZ')
    _lca.put(process)

    summary = f"""
Process "{name}" created successfully.
Flow name\tamount\tunit\ttype\tprovider:
"""
    for f in flows:
        try:
            if qref and qref.default_provider:
                summary += f"""{f["Name"]}\t{f["Amount"]}\t{f["Unit"]}\t{f["Type"]}\t({qref.default_provider.name})
    """
        except Exception as e:
            summary += f"""{f["Name"]}\t{f["Amount"]}\t{f["Unit"]}\t{f["Type"]}\t(None)
    """
    print(summary)
    return process.name
#%%
def get_flow_impacts(flows, method):
    imps = {}   
    for f in flows:
        try:
            i = get_total_impacts(f["Flow"], method)
            if i:
                for k in i:
                    i[k]["Amount"] = i[k]["Amount"] * f["Amount"]
                imps[f["Flow"]] = i
        except:
            print("Error processing flow: ", f["Flow"])
            continue
    return imps

# %%
def get_process_quantitative_flow(process):
    process_ref = _lca.find(o.Process, process)
    if process_ref == None:
        print("Process not found.")
        return None

    process = _lca.get(o.Process, process_ref.id)
    if process and process.exchanges:
        for e in process.exchanges:
            if e.is_quantitative_reference and e.flow:
                return {
                    "Name": e.flow.name,
                    "Unit": e.flow.ref_unit,
                }
    return None

#%%
class LCAFlow(BaseModel):
    Name: str
    Amount: float
    Unit: str
    Type: str
    Provider: str
    Reference: bool
    Avoided: bool

    # should behave like a dict
    def __getitem__(self, key):
        return getattr(self, key)

def biosteam_to_lca(system, product="", processes=None):
    """
    Convert a biosteam system to an openLCA process
    Product is the name of the main product 

    processes should be a list of objects with this format:
    {
        "Name": "stover production",
        "Amount": biomass.F_mass,
        "Unit": "kg",
        "Type": "Input",
        "Reference": False,
        "Provider": 'maize silage production | maize silage | APOS, U',
        "Avoided": False
    }

    """

    flows = []
    productAmount = 1
    for s in system.products:
        if "noghg" in s.ID.lower():
            continue
        print("Converting product: ", s.ID)
        try:
            if s.ID == "" or s.ID is None:
                continue
            if s.ID == product:
                print("Primary product found: ", s.ID)
                productAmount = s.F_mass
                print("Product mass: ", productAmount)

                if s.F_mass == 0:
                    print("Product mass is zero. Please make sure you simulated the system.")
                    return None

                flows.append({
                    "Name": s.ID,
                    "Amount": s.F_mass,
                    "Unit": "kg",
                    "Type": "Output",
                    "Reference": True,
                    "Provider": None,
                    "Avoided": False
                })
            else:
                rp = recommend_process(s.ID, 1)
                p = _lca.get(o.Process, name=rp)
                ref_unit = "kg"
                if p == None:
                    print("Process not found: ", s.ID)
                else:
                    if p.exchanges:
                        for f in p.exchanges:
                            if f.is_quantitative_reference and f.flow: 
                                ref_unit = f.flow.ref_unit

                flows.append({
                    "Name": s.ID,
                    "Amount": s.F_mass,
                    "Unit": ref_unit,
                    "Type": "Output",
                    "Reference": False,
                    "Provider": rp,
                    "Avoided": False
                })
        except Exception as ex:
            print("Error processing product: ", s.ID, ex)
            pass

    for s in system.feeds:
        if "noghg" in s.ID.lower():
            continue
        print("Converting feed: ", s.ID)
        try:
            if s.ID == "" or s.ID is None:
                continue
            rp = recommend_process(s.ID, 1)
            p = _lca.get(o.Process, name=rp)
            ref_unit = "kg"

            if p == None:
                print("Process not found: ", s.ID)
            else:
                if p.exchanges:
                    for f in p.exchanges:
                        if f.is_quantitative_reference and f.flow: 
                            ref_unit = f.flow.ref_unit
            flows.append({
                "Name": s.ID,
                "Amount": s.F_mass,
                "Unit": ref_unit,
                "Type": "Input",
                "Reference": False,
                "Provider": rp,
                "Avoided": False
            })
        except Exception as ex:
            print("Error processing feed: ", s.ID, ex)
            pass
            

    # electricity
    try:
        print("Converting electricity")
        if system.power_utility is None:
            print("No power utility found. Using default electricity process.")
            flows.append({
                "Name": "Process Electricity",
                "Amount": 0,
                "Unit": "kWh",
                "Type": "Input",
                "Reference": False,
                "Provider": recommend_process("Process Electricity", 1),
                "Avoided": False
            })
        else:
            flows.append({
                    "Name": "Process Electricity from the US grid",
                    "Amount": system.power_utility.rate/1000*3600,
                    "Unit": "kWh",
                    "Type": "Input",
                    "Reference": False,
                    "Provider": recommend_process("Electricity from the US grid", 1),
                    "Avoided": False
                })
    except Exception as ex:
        print("Error processing electricity: ", ex)

    # heating and cooling
    try:
        print("Converting heating and cooling")
        if system.get_cooling_duty() and system.get_cooling_duty() > 0:
            flows.append({
                "Name": "Process Cooling",
                "Amount": system.get_cooling_duty()/1000/system.operating_hours,
                "Unit": "MJ",
                "Type": "Input",
                "Reference": False,
                "Provider": recommend_process("Process Cooling", 1),
                "Avoided": False
            })
        else: 
            flows.append({
                    "Name": "Process Heating and Cooling",
                    "Amount": 0,
                    "Unit": "MJ",
                    "Type": "Input",
                    "Reference": False,
                    "Provider": recommend_process("Process Heating and Cooling", 1),
                    "Avoided": False
                })
    except Exception as ex:
        print("Error processing heating and cooling: ", ex)
    
    if processes:
        flows.extend(processes)

    normalized = []
    for f in flows:
        i = {}
        i["Name"] = f["Name"]
        i["Amount"] = f["Amount"]/productAmount
        i["Unit"] = f["Unit"]
        i["Type"] = f["Type"]
        i["Provider"] = f["Provider"]
        i["Reference"] = f["Reference"]
        i["Avoided"] = f["Avoided"]

        normalized.append(i)
    
    process = create_process(system.ID, normalized, True)
    return process

#%%
# ============================
# LCAManager for biosteam integration
# ============================

def impact_assigner(assign_func):
    """
    Decorator that handles common impact assignment logic for LCAManager methods.
    """
    def wrapper(*args, **kwargs):
       
        # Common logic: get impact categories
        categories = list(bst.settings.impact_indicators.keys())
        # Get method_id from instance (args[0] is self)
        method_id = kwargs.get('method_id', args[0].default_method_id if len(args) > 0 else "d2c781ce-21b4-3218-8fca-78133f2c8d4d")

        if not categories:
            print(f"⚠️  No impact categories available. Run setup_biosteam_categories_from_method() first.")
            return False

        # Determine process_id and type based on arguments (adjusted for class methods)
        if len(args) > 1 and hasattr(args[1], 'set_CF'):
            # Pattern: assign_impacts_to_stream(self, stream, process_id, [amount], ...)
            is_stream = True
            stream = args[1]

            # Check if process_id was provided
            if len(args) > 2:
                # process_id explicitly provided
                process_id = args[2]
                print(f"🔍 Using provided process ID: {process_id}")
            else:
                # Use stream.ID for automatic search
                process_id = stream.ID
                print(f"🤖 Auto-searching for stream '{stream.ID}' using AI...")

            # Check if amount was provided as third positional argument
            if len(args) > 3:
                user_amount = args[3]
                print(f"🔢 Using user-specified amount: {user_amount}")
            else:
                user_amount = None

        elif len(args) > 1 and isinstance(args[1], str):
            # Pattern: assign_impacts_to_electricity/steam(self, process_id, ...)
            is_stream = False
            process_id = args[1]
            user_amount = None
        else:
            raise ValueError("Invalid arguments")

        # Check if amount was provided in kwargs
        user_amount = kwargs.get('amount', user_amount)

        # Get impacts using sesalca_v2 functions
        impact_data = get_direct_flow_impacts(process_id, method_id)
        if not impact_data:
            print(f"❌ Could not get impacts for process {process_id}")
            return False

        impacts = impact_data.get('impacts', {})
        # Ensure impact_values are aligned with categories
        # Categories come from biosteam (e.g., "Global warming (kg CO2 eq)")
        # Impacts from DB might have different names (e.g., "Global warming")
        # We need to match them correctly
        impact_values = []
        for category in categories:
            # Try to find matching impact by removing the unit part
            category_name = category.rsplit(' (', 1)[0]  # Remove " (kg CO2 eq)" part
            value = impacts.get(category_name, 0.0)
            impact_values.append(value)

        basis = impact_data.get('unit', 'kg')
        # Use user-specified amount if provided, otherwise use database amount
        amount = user_amount if user_amount is not None else impact_data.get('amount', 1.0)

        if user_amount is not None:
            print(f"   ℹ️  Overriding database amount ({impact_data.get('amount', 1.0)}) with user amount ({amount})")

        # Extract multiplier if present
        multiplier = kwargs.get('multiplier', 1.0)

        # Call specific function with prepared data
        if is_stream:
            # For streams: include the stream as first parameter
            return assign_func(args[0], args[1], categories, impact_values, amount, basis)
        else:
            # For utilities: only impact data
            return assign_func(args[0], categories, impact_values, amount, basis)

    return wrapper


class LCAManager:
    """
    LCA Manager for biosteam integration using sesalca_v2 backend.

    This class provides an interface to assign LCA impacts to biosteam streams
    and utilities using the enhanced sesalca_v2 functionality.
    """

    def __init__(self, default_method_id="d2c781ce-21b4-3218-8fca-78133f2c8d4d"):
        """
        Initialize LCAManager with default method.

        Parameters:
        default_method_id (str): Default LCA method UUID
        """
        self.default_method_id = default_method_id
        save_method_info(self.default_method_id)
        # Use the correct filename that save_method_info generates
        method_file = f"impact_data/method_{self.default_method_id[:8]}.json"
        self.setup_biosteam_categories_from_method(method_info_file=method_file)
        
        self.impacts_construccion = {}

    def set_default_method(self, method_id):
        """Set default method ID"""
        self.default_method_id = method_id

    @property
    def get_indicators_category(self):
        """Get list of impact indicator categories"""
        try:
            import biosteam as bst
            return list(bst.settings.impact_indicators.keys())
        except ImportError:
            print("❌ biosteam not available")
            return []

    def setup_biosteam_categories_from_method(self, method_info_file="current_method_info.json"):
        """
        Setup biosteam impact categories directly from method information JSON.
        
        This approach uses the method info to define categories first, then we can
        assign impact values separately.
        
        Parameters:
        method_info_file (str): Path to method information JSON file
        
        Returns:
        dict: Category mapping and method information
        """

        
        print("🔧 Setting up biosteam categories from method info...")
        
        if not os.path.exists(method_info_file):
            print(f"❌ Method info file not found: {method_info_file}")
            print("Run se.save_method_info_to_json() first.")
            return None
        
        # Load method info
        with open(method_info_file, 'r', encoding='utf-8') as f:
            method_data = json.load(f)
        
        # Check for both old and new JSON formats
        if 'impact_categories' in method_data:
            # New format from sesalca.save_method_info()
            categories = method_data['impact_categories']
            method_name = method_data.get('method_name', 'Unknown Method')
        else:
            print("❌ No valid method data found in file")
            return None

        if not categories:
            print("❌ No impact categories found")
            return None

        print(f"📋 Method: {method_name}")
        print(f"📊 Setting up {len(categories)} impact categories...")

        # Define categories in biosteam
        successful_count = 0
        bst.settings.impact_indicators.clear()
        
        for category in categories:
            try:
                # Clean category name for biosteam
                original_name = category['name']
                original_units = category['ref_unit']
                bst_category = f'{original_name} ({original_units})'
                bst.settings.define_impact_indicator(key=bst_category, units='dimensionless')
                successful_count += 1
                
            except Exception as e:
                print(f"⚠️  Could not define category '{category['name']}': {e}")
        
        print(f"✅ Successfully defined {successful_count} categories in biosteam")

    @impact_assigner
    def assign_impacts_to_stream(self, stream, categories, impact_values, amount, basis):
        """
        Assign impacts to a biosteam stream.

        Public Interface:
        assign_impacts_to_stream(stream, process_id=None)
        - If process_id is provided: uses that specific process
        - If process_id is None: automatically searches using stream.ID with AI

        Internal Parameters (handled by decorator):
        stream: biosteam Stream object
        categories: List of impact categories (auto-filled)
        impact_values: List of impact values (auto-filled)
        amount: Amount for normalization (auto-filled)
        basis: Basis unit (auto-filled)
        """
        # Handle volumetric basis (m3, L, etc.) vs mass basis (kg, ton)
        if basis and ('m3' in basis.lower() or 'm³' in basis.lower()):
            # LCA data is in volumetric units but BioSTEAM streams use mass
            # Need to convert using density
            # For water-like streams, assume density = 1000 kg/m³ = 1 kg/L

            print(f"   ⚠️  Converting volumetric basis '{basis}' to mass basis 'kg'")

            # Try to get stream density if available
            try:
                # Get volumetric flow in m3/hr
                if hasattr(stream, 'get_total_flow'):
                    vol_flow_m3hr = stream.get_total_flow('m3/hr')
                    mass_flow_kghr = stream.F_mass  # kg/hr
                    if vol_flow_m3hr > 0:
                        density = mass_flow_kghr / vol_flow_m3hr  # kg/m3
                        print(f"   📊 Calculated density from stream: {density:.2f} kg/m³")
                    else:
                        density = 1000.0  # Default water density
                        print(f"   📊 Using default water density: {density:.2f} kg/m³")
                else:
                    density = 1000.0  # Default water density
                    print(f"   📊 Using default water density: {density:.2f} kg/m³")
            except Exception as e:
                density = 1000.0  # Default water density
                print(f"   ⚠️  Could not calculate density, using default: {density:.2f} kg/m³ ({e})")

            # Convert impact values from per m3 to per kg
            # impact/m3 × (m3/kg) = impact/kg
            # m3/kg = 1/density[kg/m3]
            conversion_factor = 1.0 / density  # m3/kg

            for category, value in zip(categories, impact_values):
                # Convert from impact/m3 to impact/kg
                cf_value = value * amount * conversion_factor
                # Set CF without any unit parameters - let BioSTEAM handle it
                stream.set_CF(category, cf_value)
                print(f"      {category}: {value:.4e} /m³ × {amount} → {cf_value:.4e}")

        else:
            # Mass basis (kg, ton, etc.) - apply amount multiplier directly
            for category, value in zip(categories, impact_values):
                # Apply amount multiplier (+1 for burden, -1 for credit)
                cf_value = value * amount
                # Set CF without any unit parameters - let BioSTEAM handle it
                stream.set_CF(category, cf_value)

        print(f"✅ Assigned {len(categories)} impacts to stream {stream.ID} (amount: {amount}, basis: {basis})")
        return True

    @impact_assigner
    def assign_impacts_to_electricity(self, categories, impact_values, amount, basis):
        """
        Assign impacts to electricity utility.

        Parameters:
        categories: List of impact categories
        impact_values: List of impact values
        amount: Amount for normalization (usually 1.0)
        basis: Basis unit from database (e.g., 'MJ', 'kWh')
        """
        try:
            import biosteam as bst
        except ImportError:
            print("❌ biosteam not available")
            return False

        # Convert values to the correct unit (kWh) and divide by operating_hours
        for category, value in zip(categories, impact_values):
            # Convert from MJ to kWh if needed
            if basis and ('MJ' in basis.upper() or 'megajoule' in basis.lower()):
                # 1 kWh = 3.6 MJ
                cf_kwh = value
                print(f"   Converting {category}: {value:.6e} kg/MJ → {cf_kwh:.6e} kg/kWh")
            else:
                cf_kwh = value
                if basis:
                    print(f"   Using {category}: {value:.6e} kg/{basis}")

            # CRITICAL FIX: Divide by operating_hours
            # BioSTEAM's get_net_electricity_impact() = CF × get_electricity_consumption()
            # where get_electricity_consumption() = kW × operating_hours (annual kWh)
            # To get impact per hour, we need: CF_biosteam = CF_actual / operating_hours
            operating_hours = 8000
            cf_hourly =  cf_kwh / operating_hours
            print(f"   Dividing by {operating_hours} hours: {cf_kwh:.6e} → {cf_hourly:.6e} kg/kWh")

            # Set the CF in BioSTEAM
            print(f"==="*20)
            print(f"Setting electricity CF for {category}: {cf_hourly:.6e} kg/kWh")
            print(f"==="*20)
            bst.settings.set_electricity_CF(category, cf_hourly , basis='MJ', units='dimensionless')

        print(f"✅ Assigned {len(categories)} electricity impacts (hourly basis)")
        return True

    @impact_assigner
    def assign_impacts_to_steam(self, categories, impact_values, amount, basis):
        """
        Assign impacts to steam utility.

        Parameters:
        categories: List of impact categories
        impact_values: List of impact values
        amount: Amount for normalization (usually 1.0)
        basis: Basis unit from database (e.g., 'MJ', 'kg')
        """
        try:
            import biosteam as bst
        except ImportError:
            print("❌ biosteam not available")
            return False

        # Convert values to the correct unit if needed
        # Steam/heating utilities typically use MJ or GJ
        for category, value in zip(categories, impact_values):
            # BioSTEAM expects steam CFs in terms of kJ (or MJ)
            # Check if unit conversion is needed
            if basis and ('MJ' in basis.upper() or 'megajoule' in basis.lower()):
                # Already in MJ, use directly (BioSTEAM uses kJ internally but accepts MJ)
                cf_mj = value
                print(f"   Using {category}: {value:.6e} kg/MJ")
            elif basis and ('GJ' in basis.upper() or 'gigajoule' in basis.lower()):
                # Convert from GJ to MJ
                # 1 GJ = 1000 MJ
                cf_mj = value / 1000
                print(f"   Converting {category}: {value:.6e} kg/GJ → {cf_mj:.6e} kg/MJ")
            elif basis and 'kg' in basis.lower():
                # If basis is 'kg' (natural gas kg), assume it's energy content
                # Typical: ~50 MJ/kg for natural gas
                # But we should use the value directly and let BioSTEAM handle it
                cf_mj = value
                print(f"   Using {category}: {value:.6e} kg/{basis}")
            else:
                # Use as-is
                cf_mj = value
                if basis:
                    print(f"   Using {category}: {value:.6e} kg/{basis}")

            # Set the CF in BioSTEAM
            # Note: BioSTEAM steam utilities use kJ internally, so we use 'kJ' as basis
            bst.settings.set_utility_agent_CF('low_pressure_steam', category, cf_mj/1000/8000, basis='kJ', units='dimensionless')

        print(f"✅ Assigned {len(categories)} steam impacts (basis: {basis} → kJ)")
        return True

    @impact_assigner
    def assign_impacts_to_construction(self, categories, impact_values, amount, basis):
        """
        Assign impacts to construction.

        Parameters:
        categories: List of impact categories
        impact_values: List of impact values
        amount: Amount for normalization (usually 1.0)
        basis: Basis unit from database (e.g., 'kg', 'ton')
        """
        self.impacts_construccion = {}
        # Assign construction impacts directly
        for category, value in zip(categories, impact_values):
            cf_value = value* 1
            self.impacts_construccion[category] = cf_value
            print(f"   {category}: {cf_value:.4e} per {basis}")
            #bst.settings.add_construction_CF(category, cf_value, basis='kg', units='dimensionless')

        print(f"✅ Assigned {len(categories)} construction impacts")
        return True
    
    def get_construction_impacts(self):
        return self.impacts_construccion
        
    
    def get_impacts_stream(self, stream):
        """
        Get impacts for a biosteam stream.

        Parameters:
        stream: biosteam Stream object

        Returns:
        dict: Impact values by category
        """
        indicators = self.get_indicators_category
        print(f"♻️ Getting impacts for stream {stream.ID}:")
        for indicator in indicators:
            print(f"   - {indicator}: {stream.get_impact(indicator)}")
        
        return {indicator: stream.get_impact(indicator) for indicator in indicators}


    def get_electricity_impacts(self, system: bst.System):
        """
        Get impacts for electricity utility.

        Returns:
        dict: Impact values by category
        """
        

        indicators = self.get_indicators_category
        print("⚡ Getting electricity impacts:")
        for indicator in indicators:
            print(f"   - {indicator}: {system.get_net_electricity_impact(key=indicator)}")
        
        return {indicator: system.get_net_electricity_impact(key=indicator) for indicator in indicators}
    
    def get_steam_impacts(self, system: bst.System):
        """
        Get impacts for steam utility.

        Returns:
        dict: Impact values by category
        """
        
        indicators = self.get_indicators_category
        print("🔥 Getting steam impacts:")
        for indicator in indicators:
            print(f"   - {indicator}: {system.get_net_utility_impact(key=indicator)}")

        return {indicator: system.get_net_utility_impact(key=indicator) for indicator in indicators}

    def get_environmental_flows_analysis(self, process_id, method_id=None):
        """
        Get detailed environmental flows analysis (emissions, resource consumption).

        This shows WHAT environmental impacts are happening (CO2 emissions, water use, etc.)

        Parameters:
        process_id (str): Process ID or name to analyze
        method_id (str, optional): LCA method ID. Uses default if None.

        Returns:
        list: Environmental flows with impact details by category
        """
        if method_id is None:
            method_id = self.default_method_id

        print(f"🌍 Environmental Flows Analysis for: {process_id}")
        print(f"📊 Method: {method_id[:8]}...")

        try:
            flows_data = get_flow_impacts_of_process(process_id, method=method_id)

            if flows_data:
                print(f"✅ Found {len(flows_data)} environmental flow impacts")
                # Group by impact category for better readability
                by_category = {}
                for flow in flows_data:
                    category = flow['Impact Category']
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(flow)

                for category, flows in by_category.items():
                    print(f"\n🏷️  {category}:")
                    for flow in flows[:5]:  # Show top 5 per category
                        print(f"   • {flow['Flow']}: {flow['Amount']:.2e} {flow['Unit']}")
                    if len(flows) > 5:
                        print(f"   ... and {len(flows)-5} more flows")

            return flows_data

        except Exception as e:
            print(f"❌ Error in environmental flows analysis: {e}")
            return []

    def get_supply_chain_analysis(self, process_id, method_id=None):
        """
        Get detailed supply chain flows analysis (products, services from other processes).

        This shows WHO contributes to impacts (electricity provider, transport, chemicals, etc.)

        Parameters:
        process_id (str): Process ID or name to analyze
        method_id (str, optional): LCA method ID. Uses default if None.

        Returns:
        list: Supply chain flows with contribution details by category
        """
        if method_id is None:
            method_id = self.default_method_id

        print(f"🏭 Supply Chain Analysis for: {process_id}")
        print(f"📊 Method: {method_id[:8]}...")

        try:
            flows_data = get_tech_flow_impacts(process_id, method=method_id)

            if flows_data:
                print(f"✅ Found {len(flows_data)} supply chain flow impacts")
                # Group by impact category for better readability
                by_category = {}
                for flow in flows_data:
                    category = flow['Impact Category']
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(flow)

                for category, flows in by_category.items():
                    print(f"\n🏷️  {category}:")
                    for flow in flows[:5]:  # Show top 5 per category
                        provider = flow.get('process', 'Unknown provider')
                        print(f"   • {flow['Flow']} from {provider}: {flow['Amount']:.2e} {flow['Unit']}")
                    if len(flows) > 5:
                        print(f"   ... and {len(flows)-5} more flows")

            return flows_data

        except Exception as e:
            print(f"❌ Error in supply chain analysis: {e}")
            return []
