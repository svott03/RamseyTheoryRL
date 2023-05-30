import itertools
import igraph as ig
import matplotlib.pyplot as plt
import sys

def is_complete(G):
    n = G.vcount()
    return G.ecount() == n * (n - 1) // 2


# TODO Parallelize
def has_independent_set_of_size_k(G, k):
    for sub_nodes in itertools.combinations(range(G.vcount()), k):
        subgraph = G.subgraph(sub_nodes)
        if subgraph.ecount() == 0:
            return True
    return False


# TODO Parallelize
def has_kn(G, k):
    for sub_nodes in itertools.combinations(range(G.vcount()), k):
        subgraph = G.subgraph(sub_nodes)
        if is_complete(subgraph):
            return True
    return False


def check_counterexample(G, s, t):
  return not has_kn(G, s) and not has_independent_set_of_size_k(G,t)

def change_edge(G, e):
    G.delete_edges([e]) if G.are_connected(*e) else G.add_edge(*e)


def write_counterexample(G, g6path_to_write_to):
    import os
    import networkx as nx

    # Convert igraph graph to networkx graph
    nx_graph = nx.Graph(G.get_edgelist())

    # Write the graph6 representation to a temporary file
    tempfile_path = 'temp.g6'
    nx.write_graph6(nx_graph, tempfile_path, header=False)

    # Read the graph6 data from the temporary file
    with open(tempfile_path, 'r') as temp_file:
        graph6_data = temp_file.read()

    # Append the graph6 data to the final output file
    with open(g6path_to_write_to, 'a') as file:
        file.write(graph6_data)

    # Remove the temporary file
    os.remove(tempfile_path)

    sys.stdout.write('\033[1m\033[96mCounterexample found.\033[0m\n')

def get_unique_graphs(g6path_to_read_from, g6path_to_write_to):
    import networkx as nx
    import os
    # Function to check if two graphs are isomorphic
    def are_graphs_isomorphic(G1, G2):
        return nx.is_isomorphic(G1, G2)

    # Function to find unique graphs from a list
    def find_unique_graphs(graph_list):
        unique_graphs = []
        for i in range(len(graph_list)):
            is_unique = True
            for j in range(i + 1, len(graph_list)):
                if are_graphs_isomorphic(graph_list[i], graph_list[j]):
                    is_unique = False
                    break
            if is_unique:
                unique_graphs.append(graph_list[i])
        return unique_graphs

    # Read the g6 file and load graphs into a list
    graph_list = nx.read_graph6(g6path_to_read_from)
    graph_list = [graph_list] if type(graph_list) != list else graph_list

    # Find isomorphic graphs
    isomorphic_graphs = find_unique_graphs(graph_list)
    # Graphing utilities:
    # i = 0
    # for graph in isomorphic_graphs:
    #     pos = nx.circular_layout(graph)
    #     nx.draw_networkx(graph, pos=pos)
    #     plt.savefig(f"figure_{i}.png")
    #     plt.clf()
    #     i += 1


    tempfile_path = 'temp.g6'
    for isomorphic_graph in isomorphic_graphs:
        # Write the graph6 representation to a temporary file
        nx.write_graph6(isomorphic_graph, tempfile_path, header=False)

        # Read the graph6 data from the temporary file
        with open(tempfile_path, 'r') as temp_file:
            graph6_data = temp_file.read()

        # Append the graph6 data to the final output file
        with open(g6path_to_write_to, 'a') as file:
            file.write(graph6_data)

        # Remove the temporary file
    os.remove(tempfile_path)