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
from functools import lru_cache
#%%
_lca = ipc.Client()
# search the embeddings using cosine similarity
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from datetime import datetime
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

from pydantic import BaseModel

#%%
_flows = {}
_embeddings = {}
_flow_embeddings = {}

def init():
    """
    Initializes global variables `_flows`, `_embeddings`, and `_flow_embeddings`.
    This function performs the following steps:
    1. Retrieves all flow descriptors using `_lca.get_descriptors(o.Flow)` and stores them in the `_flows` dictionary with flow names as keys.
    2. Reads process embeddings from 'process_embeddings.csv' and stores them in the `_embeddings` dictionary with process names as keys and their corresponding embeddings as values.
    3. Reads flow embeddings from 'flow_embeddings.csv' and stores them in the `_flow_embeddings` dictionary with flow names as keys and their corresponding embeddings as values.
    Raises:
        FileNotFoundError: If 'process_embeddings.csv' or 'flow_embeddings.csv' files are not found.
        ValueError: If there is an issue with parsing the embeddings from the CSV files.
    """
    global _flows
    global _embeddings
    global _flow_embeddings
    localPath = "./"
    print("Looking for embeddings in: ", sys.path)
    for p in sys.path:
        if os.path.exists(p) and os.path.isdir(p):
            for f in os.listdir(p):
                if "process_embeddings.csv" in f:
                    localPath = p + "/"
                    break

    all_flows = _lca.get_descriptors(o.Flow)
    _flows = {f.name:f for f in all_flows}
    
    _embeddings = {}
    with open(localPath+'process_embeddings.csv', 'r') as f:
        print("Reading process embeddings from: ", localPath+'process_embeddings.csv')
        lines = f.readlines()
        for line in lines[1:]:
            parts = line.split('",')
            _embeddings[parts[0].replace('\"', '')] = list(map(float, parts[1].split(',')))

    # _flow_embeddings = {}
    # with open(localPath+'flow_embeddings.csv', 'r') as f:
    #     lines = f.readlines()
    #     for line in lines[1:]:
    #         parts = line.split('",')
    #         _flow_embeddings[parts[0].replace('\"', '')] = list(map(float, parts[1].split(',')))

def get_embeddings():
    """
    Retrieves process descriptors, generates embeddings for them in batches, and saves the embeddings.
    This function performs the following steps:
    1. Retrieves process descriptors using the `_lca.get_descriptors` method.
    2. Extracts the names of the processes.
    3. Generates embeddings for the process names in batches of 2000 using the `client.embeddings.create` method.
    4. Prints the progress of the embedding generation.
    5. Extends the embeddings list with the newly created embeddings.
    6. Saves the embeddings using the `save_embeddings` method.
    Note:
        The function assumes the existence of `_lca`, `client`, and `save_embeddings` objects or methods in the scope.
    Returns:
        None
    """
    processes = _lca.get_descriptors(o.Process)
    process_names = [p.name for p in processes[0:]]
    embeddings = []
    # create embeddings in batches of 2000
    for i in range(0, len(process_names), 2000):
        print(f"Progress: {i/len(process_names)}")
        process_embeddings = client.embeddings.create(input=process_names[i:i+2000], model="text-embedding-3-small").data
        embeddings.extend(process_embeddings)
    
    save_embeddings()


def save_embeddings():
    global _embeddings
    localPath = "./"
    for p in sys.path:
        if os.path.exists(p):
            for f in os.listdir(p):
                if "process_embeddings.csv" in f:
                    localPath = p
                    break

    with open(localPath+'process_embeddings.csv', 'w') as f:
        f.write("Process,Embedding\n")
        for (k, v) in _embeddings.items():
            f.write(f'"{k}",{",".join(map(str, v))}\n')

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



def get_processes(query, n=10, _embeddings=False):
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
    global descriptors
    if query == "":
        return []
    try:
        # global _embeddings
        # if _embeddings == {}:
        #     init()
        # inEmbedding = client.embeddings.create(input=[query], model="text-embedding-3-small").data[0].embedding

        # similarity_scores = []
        # for (k, v) in _embeddings.items():
        #     similarity_scores.append([k, cosine_similarity([inEmbedding], [v])[0][0]])
        # sorted_scores = [[k, v] for k, v in sorted(similarity_scores, key=lambda item: item[1], reverse=True)]
        # processes = [x[0] for x in sorted_scores[0:number]]
        # return processes
        _n = 20 if n < 20 else n

        synonyms = [query] + get_synonyms(query, 5)
        processes = []
        if descriptors == []:
            descriptors = _lca.get_descriptors(o.Process)
        for s in synonyms:
            processes.extend([p.name for p in descriptors if s.lower() in p.name.lower()])
        processes = list(set(processes))

        return processes[0:min(len(processes), _n)]
    except Exception as e:
        print("Error getting processes for: ", query, ". " + str(e))
        return []

def recommend_process(query, n=1):
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
    try:
        _n = 20 if n < 20 else n
        processes = get_processes(query, _n)
        process = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""
                
                I have found some processes that match your query: {'; '.join(processes)}"""},
                {"role": "user", "content": f"Which of these processes is the closest match to: {query}? Prefer market processes and those for the United States. Do not explain. Respond only ith a process name that is in the list" }
            ]).choices[0].message.content

        if n == 1:
            for p in processes:
                if process in p:
                    return p
            return processes[0]
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
    if process_ref is None:
        print("Process not found.")
        return {
            "Name": process,
            "Description": "Process not found.",
            "Unit": ""
        }

    else:
        process = _lca.get(o.Process, process_ref.id)
        ref_unit = ""
        for e in process.exchanges:
            if e.is_quantitative_reference:
                ref_unit = f"{e.amount} {e.flow.ref_unit}" 
                break
        return {
            "Name": process.name,
            "Description": process.description,
            "Unit": ref_unit
        }


def get_product_system(process, location="US"):
    system_ref = _lca.find(o.ProductSystem, process)
    if system_ref != None:
        print("Product system already exists.")
        return system_ref
    
    system_ref = create_product_system(process)
    print("Product system created: ", system_ref)
    return system_ref

def get_method(method):
    methods = _lca.get_all(o.ImpactMethod)
    if len(methods) == 0:
        print("No methods found. Install the impact assessment methods in openLCA.")
        return None
    im = list(filter(lambda x: method in x.name, methods))
    if len(im) > 0:
        im = im[0]
    else:
        im = list(filter(lambda x: "EF 3.0" in x.name, methods))
        if len(im) > 0:
            im = im[0]
        else:
            im = methods[0]
            print("Method not found. Using default method: ", im.name)
    return im

@lru_cache(maxsize=128)
def get_result(process, method):
    try:
        system_ref = get_product_system(process)
        if system_ref is None:
            print("Error getting product system in get_result. Returning None")
            return None
        im = get_method(method)

        system_ref.location = "US"

        print("Using method: ", im.name)
        setup = o.CalculationSetup(
            target=o.Ref(
                ref_type=o.RefType.ProductSystem,
                id=system_ref.id,
                location="US"
            ),
            impact_method=im, # EF 3.1 Method (adapted)
            # nw_set=o.Ref(id="867fe119-0b5c-38a0-a3e6-1d845ffaedd5"),
        )

        result: ipc.Result = _lca.calculate(setup)
        result.wait_until_ready()
        # print("Result ready: ", result)
        _lca.delete(system_ref)
        return result
    except Exception as ex:
        print("Error in get_result: ", ex)
        return None

def get_total_impacts(process, _method="EF 3.0", result=None):
    """
    Calculate the total environmental impacts for a given process using a specified impact assessment method.
    Parameters:
    process (str): The name or identifier of the process for which to calculate impacts.
    _method (str, optional): The impact assessment method to use. Defaults to "EF 3.0".
    result (object, optional): Precomputed result object. If None, the result will be computed using the process and method. Defaults to None.
    Returns:
    dict: A dictionary where keys are impact category names (with reference units) and values are the total impact amounts.
          Returns a dictionary with zero impacts if the result cannot be obtained.
          Returns None if an exception occurs during the calculation.
    """
    try:
        if result is None:
            result = get_result(process, _method)
            if result is None:
                print("Error getting result. Returning zero impacts")
                # delete_product_system(process)
                method = get_method(_method)
                return {f"{i.name}": 0 for i in _lca.get(o.ImpactMethod, method.id).impact_categories}
        
        print(f"Getting total impacts for {process}")
        # delete_product_system(process)
        results = {f"{impact.impact_category.name} ({impact.impact_category.ref_unit})": impact.amount for impact in result.get_total_impacts()}
        results["Amount"] = result.get_demand().amount 
        results["Unit"] = result.get_demand().tech_flow.flow.ref_unit
        results["Location"] = result.get_demand().tech_flow.provider.location
        result.dispose()
        return results
    
    except Exception as ex:
        print("Error in get_total_impacts: ", ex)
        method = get_method(_method)
        return {f"{i.name}": 0 for i in _lca.get(o.ImpactMethod, method.id).impact_categories}

def delete_product_system(process):
    return
    print(f"Deleting product system for {process}")
    ps = _lca.get_all(o.ProductSystem)
    for p in ps:
        if process in p.name:
            print("Found product system: ", p)
            _lca.delete(p)
            print(f"Deleted product system for {process}")
            return True 
    print(f"Product system for {process} not found.")
    return False
# %%
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
                            result is None. Default is "EF 3.0".

    Returns:
    list: A list of dictionaries, each containing the following keys:
        - "Flow ID": The ID of the flow.
        - "Impact Category": The name of the impact category.
        - "Flow": The name of the flow.
        - "Category": The category of the flow.
        - "Amount": The amount of the flow impact.
        - "Unit": The unit of the flow impact.
    """
    if result is None:
        if method is None:
            method = "EF 3.0"
        result = get_result(process, method)
        if result is None:
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
def get_tech_flow_impacts(process, result=None, method=None):
    if result is None:
        if method is None:
            method = "EF 3.0"
        result = get_result(process, method)
        if result is None:
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
def get_direct_flow_impacts(process, method="EF 3.0"):
    flows = {}

    result = get_result(process, method)
    if result is None:
        return flows 

    tfs = result.get_tech_flows()
    for f in tfs:
        impacts = result.get_direct_impacts_of(f)
        if f.flow.name not in flows:
            flows[f.flow.name] = {k.impact_category.name:0 for k in impacts}
        for i in impacts:
            flows[f.flow.name][i.impact_category.name] += i.amount

    result.dispose()
    return flows

    
    # print(f"Getting direct flow impacts for {process}")
    # print(f"There are {len(p.exchanges)} exchanges")
    # for i, e in enumerate(p.exchanges):
    #     try:
    #         print(f"Processing exchange {i+1}")
    #         defaultProvider = e.default_provider
    #         if defaultProvider:
    #             provider = _lca.get(o.Process, defaultProvider.id)
    #             if provider:
    #                 result = get_result(provider.name, method)
    #                 if result is None:
    #                     print("Error getting result for provider: ", provider.name)
    #                     delete_product_system(provider.name)
    #                     continue
    #                 directFlowImpacts = get_total_impacts(provider.name, method, result)
    #                 directFlowImpacts[f"Amount"] = e.amount
    #                 directFlowImpacts[f"Unit"] = e.flow.ref_unit
    #                 directFlowImpacts[f"Provider"] = e.flow.name
    #                 directFlowImpacts[f"Input"] = e.is_input
    #                 directFlowImpacts[f"Avoided"] = e.is_avoided_product
                    
    #                 impacts[f"{i}:{e.flow.name}"] = directFlowImpacts
    #                 result.dispose()


    #     except Exception as ex:

    #         print("Error processing exchange: ", e.flow.name, "\n", ex)
    #         continue

    # return impacts
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
    system_ref.location = process_ref.location
    return system_ref

def delete_process(name):
    process = _lca.find(o.Process, name)
    if process is None:
        print("Process not found.")
        return None
    _lca.delete(process)
    return process

#%%
def find_flows(name):
    global _flows
    matches = []
    if _flows == {}:
        init()
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
def recommend_flow(query, n=1):
    global _flow_embeddings
    if _flow_embeddings == {}:
        init()
    inEmbedding = client.embeddings.create(input=[query], model="text-embedding-3-small").data[0].embedding

    similarity_scores = []
    for (k, v) in _flow_embeddings.items():
        similarity_scores.append([k, cosine_similarity([inEmbedding], [v])[0][0]])
    sorted_scores = [[k, v] for k, v in sorted(similarity_scores, key=lambda item: item[1], reverse=True)]
    flows = [x[0] for x in sorted_scores[0:10]]

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

        if provider is None:
            print("Provider not found: ", p)
            
            rf = _lca.get(o.Flow, name=f["Name"])
            if rf is None:
                print("Flow not found: ", f["Name"])
                group = [u for u in _lca.get_descriptors(o.UnitGroup) if "Sesalca units " + f["Unit"] in u.name]
                if len(group) == 0:
                    group = o.new_unit_group("Sesalca units " + f["Unit"], f["Unit"])
                    group.last_change =  datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%zZ')
                    print("New group: ", group)
                    _lca.put(group)
                else:
                    group = _lca.get(o.UnitGroup, group[0].id)
                unit = _lca.get(o.FlowProperty, name=f["Unit"])
                if unit is None:
                    unit = o.new_flow_property(f["Unit"], group)
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
            for e in provider.exchanges:
                if e.is_quantitative_reference:
                    rf = e.flow
                    break

        if f["Type"] == "Input":
            qref = o.new_input(process, rf, f["Amount"])
        elif f["Type"] == "Output":
            qref = o.new_output(process, rf, f["Amount"])
        elif f["Type"] == "Product":
            qref = o.new_output(process, rf, f["Amount"])
        elif f["Type"] == "Waste":
            qref = o.new_output(process, rf, f["Amount"])
        else:
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
        summary += f"""{f["Name"]}\t{f["Amount"]}\t{f["Unit"]}\t{f["Type"]}\t({qref.default_provider.name})
"""
    print(summary)
    return process.name
#%%
def get_flow_impacts(flows, method):
    imps = {}   
    for f in flows:
        try:
            i = get_total_impacts(f["Flow"], method)
            for k in i:
                i[k]["Amount"] = i[k]["Amount"] * f["Amount"]
            imps[f["Flow"]] = i
        except:
            print("Error processing flow: ", f["Flow"])
            continue
    print(imps)
    return imps

# %%
def get_process_quantitative_flow(process):
    process_ref = _lca.find(o.Process, process)
    if process_ref is None:
        print("Process not found.")
        return None

    process = _lca.get(o.Process, process_ref.id)
    for e in process.exchanges:
        if e.is_quantitative_reference:
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
                if p is None:
                    print("Process not found: ", s.ID)
                else:
                    for f in p.exchanges:
                        if f.is_quantitative_reference: 
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

            if p is None:
                print("Process not found: ", s.ID)
            else:
                for f in p.exchanges:
                    if f.is_quantitative_reference: 
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
        flows.append({
                "Name": "Process Heating and Cooling",
                "Amount": system.get_heating_duty()/1000/system.operating_hours,
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
# rp = recommend_process("ethanol production", 1)
# rp 
# # %%
# r = get_result(rp, "EF 3.0")
# r
# # %%
# r2 = get_result(rp, "EF 3.0")
# r2 
# # %%
# ti = get_total_impacts(rp, "EF 3.0", r)
# ti 