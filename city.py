from dataclasses import dataclass  # type: ignore
from typing import Union, Optional, TextIO, List, Tuple, TypeAlias
from staticmap import StaticMap, CircleMarker, Line  # type: ignore
import networkx as nx  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import osmnx as ox  # type: ignore
import restaurants  # type: ignore
import metro  # type: ignore
import pickle  # type: ignore
import time  # type: ignore
import os  # type: ignore

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
    g: OsmnxGraph = ox.graph_from_place('Barcelona, Catalonia, Spain',
                                        simplify=True, network_type='walk')
    return g


def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    """Saves graph g in file named filename"""
    pickle_out = open(filename, "wb")
    pickle.dump(g, pickle_out)
    pickle_out.close()


def load_osmnx_graph(filename: str) -> OsmnxGraph:
    """Returns the graph stored in the file named filename"""
    if os.path.exists(filename):
        pickle_in = open(filename, "rb")
        g: OsmnxGraph = pickle.load(pickle_in)
        pickle_in.close()
    else:
        g = get_osmnx_graph()
        save_osmnx_graph(g, filename)
    return g


def save_city_graph(g: CityGraph, filename: str) -> None:
    """Saves graph g in file named filename"""
    pickle_out = open(filename, "wb")
    pickle.dump(g, pickle_out)
    pickle_out.close()


def load_city_graph(filename: str) -> CityGraph:
    if os.path.exists(filename):
        pickle_in = open(filename, "rb")
        g: CityGraph = pickle.load(pickle_in)
        pickle_in.close()
    else:
        g1: OsmnxGraph = load_osmnx_graph("barcelona_walk")
        g2: MetroGraph = metro.get_metro_graph()
        g = build_city_graph(g1, g2)
        save_city_graph(g, filename)
    return g


def add_g1(g: CityGraph, g1: OsmnxGraph) -> None:

    # for each node and its neighbours' information ...
    for u, nbrsdict in g1.adjacency():
        x_u: float = g1.nodes[u]["x"]
        y_u: float = g1.nodes[u]["y"]
        coord_u: Coord = (x_u, y_u)
        g.add_node(u, type="Street", position=coord_u)
        # for each adjacent node v and its (u, v) edges' information ...
        for v, edgesdict in nbrsdict.items():
            x_v: float = g1.nodes[v]["x"]
            y_v: float = g1.nodes[v]["y"]
            coord_v: Coord = (x_v, y_v)
            g.add_node(v, type="Street", position=coord_v)

            edge_type: str = "Street"
            # Hem de calcular la distancia dels edges del graf OsmnxGraph; en
            # canvi cada aresta del MetroGraph té guardada la seva distancia
            # osmnx graphs are multigraphs, but we will just consider their
            # first edge
            eattr = edgesdict[0]    # eattr contains the attributes of the
            # first edge we remove geometry information from eattr because we
            # don't need it and take a lot of space
            distance: float = eattr["length"]
            col_id: str = "#fffc38"
            edge = Edge(edge_type, distance, col_id)
            speed: float = 1.5
            time: float = distance / speed
            g.add_edge(u, v, info=edge, weight=time)


def add_g2(g: CityGraph, g2: MetroGraph) -> None:
    for node in list(g2.nodes):
        node_type: str = str(type(g2.nodes[node]["info"]))[14:-2]
        # <class 'metro.Station'>; <class 'metro.Access'>
        coord: Coord = g2.nodes[node]["position"]
        g.add_node(node, type=node_type, position=coord)

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
        g.add_edge(e[0], e[1], info=edge, weight=time)


def connect_accesses_to_closest_intersection(g: CityGraph,
                                             g1: OsmnxGraph) -> None:
    accesses_list: metro.Accesses = metro.read_accesses()
    for access in accesses_list:
        closest_node, distance = ox.distance.nearest_nodes(g1,
                                                           access.position[0],
                                                           access.position[1],
                                                           return_dist=True)
        # 562726252 = Id node; 35,8m = distancia entre access i node
        edge = Edge("Street", distance, "#fbac2c")
        speed: float = 1.5
        time: float = distance / speed
        g.add_edge(access.id, closest_node, info=edge, weight=time)


def build_city_graph(g1: OsmnxGraph, g2: MetroGraph) -> CityGraph:
    # fusió de g1 (nodes: Street; edges: Street) i g2 (nodes: Station, Access;
    # edges: enllaç, access, tram)
    g = nx.Graph()
    add_g1(g, g1)
    add_g2(g, g2)
    connect_accesses_to_closest_intersection(g, g1)
    g.remove_edges_from(nx.selfloop_edges(g))
    return g  # Fusio de tots els carrers i el graf metro


def get_closest_node(ox_g: OsmnxGraph, position: Coord) -> NodeID:
    x: float = position[0]
    y: float = position[1]
    node: NodeID = ox.distance.nearest_nodes(ox_g, x, y)
    return node


def find_path(ox_g: OsmnxGraph, g: CityGraph, src: Coord, dst: Coord) -> Path:
    src_node: NodeID = get_closest_node(ox_g, src)
    dst_node: NodeID = get_closest_node(ox_g, dst)
    path: Path = nx.shortest_path(g, source=src_node, target=dst_node,
                                  weight="weight", method='dijkstra')
    return path


def find_time_path(g: CityGraph, p: Path) -> int:
    total_time: float = 0
    for i in range(len(p) - 1):
        total_time += float(g[p[i]][p[i + 1]]["weight"])

    return int(total_time // 60)


def show(g: CityGraph) -> None:
    # mostra g de forma interactiva en una finestra
    pos = nx.get_node_attributes(g, 'position')
    nx.draw(g, pos, node_size=10)
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
    """Prints the representation of a graph on top of a map with nodes painted
       in black and edges in different colors, depending on the line they
       represent."""
    # We create the list edges which is a list of edges, each one represented
    # as a Tuple of two nodes.
    # edges: List[Tuple[str, str]] = list(g.edges)
    # We create the dictionary pos that contains the position of every node in
    # the graph.
    pos = nx.get_node_attributes(g, 'position')
    # We create the empty map
    m = StaticMap(3000, 4000, 80)
    for edge in list(g.edges):
        nodeA = edge[0]
        nodeB = edge[1]
        # We get the position of the two nodes that connect the edge i
        pos_node_A: Coord = (pos[nodeA][0], pos[nodeA][1])
        pos_node_B: Coord = (pos[nodeB][0], pos[nodeB][1])
        # We add the two nodes to the map with the functin add_marker() as
        # circles.
        color_nodeA: str = node_color(g, nodeA)
        color_nodeB: str = node_color(g, nodeB)
        # We get the color of the line that connects NodeA and NodeB getting
        # the attribute "col_id" of the edge i.
        col_id: str = g[edge[0]][edge[1]]["info"].col_id
        # We add the edge that connects NodeA and NodeB to the map.
        paint_union_two_points(m, pos_node_A, pos_node_B, color_nodeA, color_nodeB, col_id)
    # We save the map.
    image = m.render()
    image.save(filename)


def paint_union_two_points(m: StaticMap, point_A: Coord, point_B: Coord,
                     color_A: str, color_B: str, color_line: str) -> None:
    m.add_marker(CircleMarker(point_A, color_A, 8))
    m.add_marker(CircleMarker(point_B, color_B, 8))
    m.add_line(Line((point_A, point_B), color_line, 5))


def plot_path(g: CityGraph, p: Path, filename: str, src: Coord,
              dst: Coord) -> None:
    # mostra el camí p en l'arxiu filename
    # We create the empty map
    m = StaticMap(500, 500)

    pos_node_src: Coord = g.nodes[p[0]]["position"]
    paint_union_two_points(m, src, pos_node_src, "black", "black", "black")

    for i in range(len(p) - 1):
        pos_node_A: Coord = g.nodes[p[i]]["position"]
        pos_node_B: Coord = g.nodes[p[i + 1]]["position"]
        if g[p[i]][p[i + 1]]["info"].edge_type == "Street":
            color: str = "black"
        else:
            color = g[p[i]][p[i + 1]]["info"].col_id
        m.add_line(Line((pos_node_A, pos_node_B), color, 5))

    pos_node_dst: Coord = g.nodes[p[-1]]["position"]
    paint_union_two_points(m, pos_node_dst, dst, "black", "black", "black")

    # We save the map.
    image = m.render()
    image.save(filename)

# def main():
#     g1: OsmnxGraph = load_osmnx_graph("barcelona_walk")
#     # g2: MetroGraph = metro.get_metro_graph()
#     # g: CityGraph = build_city_graph(g1, g2)
#     # save_osmnx_graph(g, "city_graph_21")
#     g: CityGraph = load_city_graph("city_graph")
#     # show(g)
#     # plot(g, 'city_map_412.png')
#     # print("NODES:", g.number_of_nodes())
#     # print("EDGES:", g.number_of_edges())
#     a: Coord = restaurants.find("crep", restaurants.read())[0].position
#     b: Coord = restaurants.find("Restaurant Garlana",
#     restaurants.read())[0].position
#     x = find_path(g1, g, a, b)
#     plot_path(g, x, "test011.png", a, b)
#     # print(find_time_path(g, x))
#
#
# start_time = time.time()
# main()
# print("--- %s seconds ---" % (time.time() - start_time))
