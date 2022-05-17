from dataclasses import dataclass
from typing import Union, Optional, TextIO, List, Tuple, TypeAlias
from staticmap import StaticMap, CircleMarker, Line
import networkx as nx
import matplotlib.pyplot as plt
import osmnx as ox
import restaurants
import metro
import pickle
import time # MEASURE TIME
import os

CityGraph: TypeAlias = nx.Graph
MetroGraph: TypeAlias = nx.Graph
OsmnxGraph: TypeAlias = nx.MultiDiGraph

Coord: TypeAlias = Tuple[float, float]

NodeID: TypeAlias = Union[int, str]
Path: TypeAlias = List[NodeID]

@dataclass
class Edge:
    edge_type: str
    distance: float
    col_id: str

def get_osmnx_graph() -> OsmnxGraph:
    """Returns a osmnxgraph"""
    g: OsmnxGraph = ox.graph_from_place('Barcelona, Catalonia, Spain', simplify=True, network_type='walk')
    return g

def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    """Saves graph g in file named filename"""
    pickle_out = open(filename,"wb")
    pickle.dump(g, pickle_out)
    pickle_out.close()

def load_osmnx_graph(filename: str) -> OsmnxGraph:
    """Returns the graph stored in the file named filename"""
    if os.path.exists(filename):
        pickle_in = open(filename,"rb")
        g: OsmnxGraph = pickle.load(pickle_in)
        pickle_in.close()
    else:
        g = get_osmnx_graph()
        save_osmnx_graph(g, filename)
    return g

def save_city_graph(g: CityGraph, filename: str) -> None:
    """Saves graph g in file named filename"""
    pickle_out = open(filename,"wb")
    pickle.dump(g, pickle_out)
    pickle_out.close()

def load_city_graph(filename: str) -> CityGraph:
    if os.path.exists(filename):
        pickle_in = open(filename,"rb")
        g: CityGraph = pickle.load(pickle_in)
        pickle_in.close()
    else:
        g1: CityGraph = load_osmnx_graph("barcelona_walk")
        g2: MetroGraph = metro.get_metro_graph()
        g = build_city_graph(g1, g2)
        save_city_graph(g, filename)
    return g

def add_g1(g: CityGraph, g1: OsmnxGraph) -> None:

    # for each node and its neighbours' information ...
    for u, nbrsdict in g1.adjacency():
        x: float = g1.nodes[u]["x"]
        y: float = g1.nodes[u]["y"]
        coord: Coord = (x,y)
        g.add_node(u, type = "Street", position = coord)
        # for each adjacent node v and its (u, v) edges' information ...
        for v, edgesdict in nbrsdict.items():
            x: float = g1.nodes[v]["x"]
            y: float = g1.nodes[v]["y"]
            coord: Coord = (x,y)
            g.add_node(v, type = "Street", position = coord)

            edge_type: str = "Street"
            # Hem de calcular la distancia dels edges del graf OsmnxGraph; en canvi cada aresta del MetroGraph té guardada la seva distancia
            # osmnx graphs are multigraphs, but we will just consider their first edge
            eattr = edgesdict[0]    # eattr contains the attributes of the first edge
            # we remove geometry information from eattr because we don't need it and take a lot of space
            distance: float = eattr["length"]
            col_id: str = "#fffc38"
            edge = Edge(edge_type, distance, col_id)
            speed: float = 1.5
            time: float = distance / speed
            g.add_edge(u, v, info = edge, weight = time)

def add_g2(g: CityGraph, g2: MetroGraph) -> None:
    for node in list(g2.nodes):
        node_type: str = str(type(g2.nodes[node]["info"]))[14:-2] # <class 'metro.Station'>
        coord: Coord = g2.nodes[node]["position"]
        g.add_node(node, type = node_type, position = coord)

    for e in list(g2.edges):
        edge_type: str = g2[e[0]][e[1]]["info"].edge_type
        distance: float = g2[e[0]][e[1]]["info"].distance
        col_id: str = g2[e[0]][e[1]]["info"].col_id
        if edge_type == "tram":
            speed: float = 8
        else:
            speed = 1.5
        edge = Edge(edge_type, distance, col_id)
        time: float = distance / speed
        g.add_edge(e[0], e[1], info = edge, weight = time)

def connect_accesses_to_closest_street(g: CityGraph) -> None:
    accesses_list: metro.Accesses = metro.read_accesses()
    for access in accesses_list:
        min_dist: float = float('inf')
        closest_node = None
        for node in g.nodes:
            if g.nodes[node]["type"] == "Street" and metro.get_distance(access.position, g.nodes[node]["position"]) < min_dist:
                min_dist = metro.get_distance(access.position, g.nodes[node]["position"])
                closest_node = node
        edge = Edge("Street", min_dist, "#fbac2c")
        speed: float = 1.5
        time: float = distance / speed
        g.add_edge(access.id, closest_node, info = edge, weight = time)

def build_city_graph(g1: OsmnxGraph, g2: MetroGraph) -> CityGraph:
    # fusió de g1 (nodes: Street; edges: Street) i g2 (nodes: Station, Access; edges: enllaç, access, tram)
    g = nx.Graph()
    add_g1(g, g1)
    add_g2(g, g2)
    connect_accesses_to_closest_street(g)
    g.remove_edges_from(nx.selfloop_edges(g))
    return g

def find_closest_node(g: CityGraph, position: Coord) -> NodeID:
    min_dist: float = float('inf')
    closest_node: NodeID = None
    for node in list(g.nodes):
       if metro.get_distance(g.nodes[node]["position"], position) < min_dist:
           min_dist = metro.get_distance(g.nodes[node]["position"], position)
           closest_node = node
    return closest_node

def find_path(g: CityGraph, src: Coord, dst: Coord) -> Path:
    id_src_node: NodeID = find_closest_node(g, src)
    id_dst_node: NodeID = find_closest_node(g, dst)
    path: Path = nx.shortest_path(g, source = id_src_node, target = id_dst_node, weight = "weight", method='dijkstra')
    return path

def find_time_path(g: CityGraph, p: Path) -> int:
    total_time: float = 0
    for i in range(len(p) - 1):
        total_time += float(g[p[i]][p[i + 1]]["time"])

    return total_time // 60

def show(g: CityGraph) -> None:
    # mostra g de forma interactiva en una finestra
    pos = nx.get_node_attributes(g,'position')
    nx.draw(g, pos, node_size = 10)
    plt.show()

def node_color(g: CityGraph, node: str) -> str:
    if g.nodes[node]["type"] == "Station":
        color: str = "red"
    elif g.nodes[node]["type"] == "Access":
        color = "black"
    else:
        color = "#0f7f13"
    return color

def plot(g: CityGraph, filename: str) -> None:
    """Prints the representation of a graph on top of a map with nodes painted in black and edges in different colors, depending on the line they represent."""
    # We create the list edges which is a list of edges, each one represented as a Tuple of two nodes.
    edges: List[Tuple[str, str]] = list(g.edges)
    # We create the dictionary pos that contains the position of every node in the graph.
    pos = nx.get_node_attributes(g,'position')
    # We create the empty map
    m = StaticMap(3000, 4000, 80)
    for i in range(len(edges)):
        nodeA = edges[i][0]
        nodeB = edges[i][1]
        # We get the position of the two nodes that connect the edge i
        pos_node_A: Coord = (pos[nodeA][0], pos[nodeA][1])
        pos_node_B: Coord = (pos[nodeB][0], pos[nodeB][1])
        # We add the two nodes to the map with the functin add_marker() as circles.
        color_nodeA: str = node_color(g, nodeA)
        color_nodeB: str = node_color(g, nodeB)
        m.add_marker(CircleMarker(pos_node_A, color_nodeA, 8))
        m.add_marker(CircleMarker(pos_node_B, color_nodeB, 8))
        # We get the color of the line that connects NodeA and NodeB getting the attribute "col_id" of the edge i.
        col_id: str = g[edges[i][0]][edges[i][1]]["info"].col_id
        # We add the edge that connects NodeA and NodeB to the map.
        m.add_line(Line((pos_node_A, pos_node_B), col_id, 5))
    # We save the map.
    image = m.render()
    image.save(filename)

def plot_path(g: CityGraph, p: Path, filename: str, src: Coord, dst: Coord) -> None:
    # mostra el camí p en l'arxiu filename
    # We create the empty map
    m = StaticMap(1000, 1000)
    m.add_marker(CircleMarker(src, "black", 8))
    pos_node_src: Coord = g.nodes[p[0]]["position"]
    m.add_marker(CircleMarker(pos_node_src, "black", 8))
    m.add_line(Line((src, pos_node_src), "black", 3))
    for i in range(len(p) - 1):
        pos_node_A: Coord = g.nodes[p[i]]["position"]
        pos_node_B: Coord = g.nodes[p[i + 1]]["position"]
        if g[p[i]][p[i + 1]]["info"].edge_type == "Street":
            color: str = "black"
        else:
            color: str = g[p[i]][p[i + 1]]["info"].col_id
        m.add_line(Line((pos_node_A, pos_node_B), color, 3))
    pos_node_dst: Coord = g.nodes[p[-1]]["position"]
    m.add_marker(CircleMarker(pos_node_dst, "black", 8))
    m.add_marker(CircleMarker(dst, "black", 8))
    m.add_line(Line((pos_node_dst, dst), "black", 3))
    # We save the map.
    image = m.render()
    image.save(filename)

def main():
    # g1: CityGraph = load_osmnx_graph("barcelona_walk")
    # g2: MetroGraph = metro.get_metro_graph()
    # g = build_city_graph(g1, g2)
    # save_osmnx_graph(g, "city_graph")
    g: CityGraph = load_osmnx_graph("city_graph")
    # show(g)
    # plot(g, 'city_map2.png')
    # print("NODES:", g.number_of_nodes())
    # print("EDGES:", g.number_of_edges())
    a: Coord = g.nodes[9556190193]["position"]
    b: Coord = restaurants.find("Restaurant Garlana", restaurants.read())[0].position
    x = find_path(g, a, b)
    plot_path(g, x, "test2.png", a, b)
    print(find_time_path(g, x))


start_time = time.time()
main()
print("--- %s seconds ---" % (time.time() - start_time))
