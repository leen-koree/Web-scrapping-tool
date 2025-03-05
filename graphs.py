import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os
import arabic_reshaper
from bidi.algorithm import get_display
from d3graph import d3graph, vec2adjmat

def generate_graphs(file_path):    
    # Load the CSV file
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    
    # Define output folder based on file path
    base_folder = os.path.dirname(file_path)
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    output_folder = os.path.join(base_folder, f"{file_name}_graphs")
    os.makedirs(output_folder, exist_ok=True)
    
    # Initialize a graph
    G = nx.Graph()
    
    # Get unique labels
    unique_labels = df['Label'].unique()
    
    # Add central hub nodes
    for label in unique_labels:
        G.add_node(label, label="Hub", hub=True, type=label)
    
    # Add individual nodes and connect to their hubs
    for _, row in df.iterrows():
        entity = row['Entity']
        label = row['Label']
        occurrences = row['Occurrences']
    
        # Add the entity as a node
        G.add_node(entity, label=label, occurrences=occurrences, type=label)
    
        # Connect the entity to its corresponding hub
        if G.has_edge(label, entity):
            G[label][entity]["weight"] += occurrences
        else:
            G.add_edge(label, entity, weight=occurrences)
    
    # Define colors for each hub
    hub_colors = {
        "Date": "lightblue",
        "Person": "lightcoral",
        "Place": "lightgreen",
        "Country": "orange",
        "Location": "gray"
    }
    
    # Function to reshape Arabic text for proper display
    def reshape_text(text):
        try:
            return get_display(arabic_reshaper.reshape(str(text)))
        except Exception:
            return str(text)
    
    # Function to plot and save individual graphs for each entity
    def plot_entity_graph(hub_label, output_path):
        subgraph = nx.Graph()
    
        # Add the hub node
        subgraph.add_node(hub_label, hub=True)
    
        # Add nodes and edges for the current hub
        for node, attr in G.nodes(data=True):
            if attr.get('label') == hub_label:
                subgraph.add_node(node, **attr)
                subgraph.add_edge(hub_label, node, weight=G[hub_label][node]['weight'])
    
        # Define positions for nodes
        pos = nx.spring_layout(subgraph, seed=42)
    
        # Define colors and sizes for the subgraph nodes
        node_colors = []
        node_sizes = []
        for node, attr in subgraph.nodes(data=True):
            if attr.get('hub', False):
                node_colors.append(hub_colors.get(hub_label, "gray"))
                node_sizes.append(3000)  # Larger size for hub nodes
            else:
                node_colors.append(hub_colors.get(hub_label, "gray"))
                node_sizes.append(2000)  # Standard size for individual nodes
    
        # Reshape labels for Arabic support
        labels = {node: reshape_text(node) for node in subgraph.nodes()}
    
        # Plot the graph
        plt.figure(figsize=(12, 10))
        nx.draw_networkx_nodes(subgraph, pos, node_size=node_sizes, node_color=node_colors, alpha=0.9)
        nx.draw_networkx_edges(subgraph, pos, width=1.0, alpha=0.5)
        nx.draw_networkx_labels(subgraph, pos, labels, font_size=9, font_weight='bold')
    
        # Edge labels
        edge_labels = nx.get_edge_attributes(subgraph, 'weight')
        edge_labels = {k: reshape_text(str(v)) for k, v in edge_labels.items()}  # Ensure Arabic numbers render correctly
        nx.draw_networkx_edge_labels(subgraph, pos, edge_labels=edge_labels, font_size=7)
    
        plt.title(reshape_text(f"{hub_label} Graph"), fontsize=16)
        plt.axis('off')
    
        # Save the graph to the file path
        plt.savefig(output_path, format='png', dpi=300)
        plt.close()
    
    
    # Generate and save graphs for each entity type
    for hub in unique_labels:
        output_path = os.path.join(output_folder, f"{hub}_graph.png")
        plot_entity_graph(hub, output_path)
    
    # Add node attributes for better visualization in Gephi
    for node, attr in G.nodes(data=True):
        G.nodes[node]['label'] = node  # Use the entity name as the label
        G.nodes[node]['occurrences'] = attr.get('occurrences', 0)  # Frequency
        G.nodes[node]['type'] = 'Hub' if attr.get('hub', False) else attr.get('type', '')  # Entity type
    
    # Add edge attributes
    for u, v, attr in G.edges(data=True):
        G[u][v]['weight'] = attr.get('weight', 1)
    
    # Export to GEXF with attributes
    output_file = os.path.join(output_folder, "enhanced_graph_with_attributes.gexf")
    nx.write_gexf(G, output_file)

def generate_interactive_graph(csv_file_path):
    """
    Generates an interactive graph from a CSV file.
    
    Parameters:
        csv_file_path (str): Path to the CSV file.
    """
    # Load CSV file
    df = pd.read_csv(csv_file_path, encoding="utf-8-sig").rename(columns=str.strip)
    
    # Extract necessary columns
    source = df["Label"].tolist()  # Labels as source nodes
    target = df["Entity"].tolist()  # Entities as target nodes
    weight = df["Occurrences"].tolist()  # Occurrences as edge weights
    
    # Convert data into an adjacency matrix
    adjmat = vec2adjmat(source, target, weight=weight)
    
    # Initialize the D3 graph
    d3 = d3graph()
    d3.graph(adjmat)
    
    # Show the interactive graph
    d3.show()
   
