from dataclasses import dataclass  # type: ignore
from typing import Union, Optional, TextIO, List, Tuple, TypeAlias
import networkx as nx  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import pandas as pd  # type: ignore
import requests  # type: ignore
import io  # type: ignore
from staticmap import StaticMap, CircleMarker, Line  # type: ignore
from haversine import haversine  # type: ignore

MetroGraph: TypeAlias = nx.Graph

Coord: TypeAlias = Tuple[float, float]


@dataclass
class Station:
    id: int
    name: str
    line: str
    color_line: str
    position: Coord
    type: str


@dataclass
class Access:
    id: int
    access_name: str
    station_name: str
    station_id: int
    position: Coord
    type: str


@dataclass
class Edge:
    edge_type: str
    distance: float
    col_id: str


Stations: TypeAlias = List[Station]
Accesses: TypeAlias = List[Access]


def read_stations() -> Stations:
    """Returns a list of all stations, some are repeated"""
    url = 'estacions.csv'
    # Read the csv file and keep only few columns
    df = pd.read_csv(url, usecols=["ID_ESTACIO_LINIA", "NOM_ESTACIO",
                                   "NOM_LINIA", "COLOR_LINIA", "GEOMETRY"])
    stations_list: Stations = []
    for row in df.itertuples():
        coord: List[str] = row.GEOMETRY[7:-1].split()
        position: Coord = (float(coord[0]), float(coord[1]))
        s = Station(row.ID_ESTACIO_LINIA, row.NOM_ESTACIO, row.NOM_LINIA,
                    "#" + row.COLOR_LINIA, position, "Station")
        stations_list.append(s)
    return stations_list


def read_accesses() -> Accesses:
    """Returns a list of all accesses"""
    url = 'accessos.csv'
    # Read the csv file and keep only few columns
    df = pd.read_csv(url, usecols=["CODI_ACCES", "NOM_ACCES", "NOM_ESTACIO",
                                   "ID_ESTACIO", "GEOMETRY"])
    accesses_list: Accesses = []
    for row in df.itertuples():
        coord: List[str] = row.GEOMETRY[7:-1].split()
        position: Coord = (float(coord[0]), float(coord[1]))
        a = Access(row.CODI_ACCES, row.NOM_ACCES, row.NOM_ESTACIO,
                   row.ID_ESTACIO, position, "Access")
        accesses_list.append(a)
    return accesses_list


def get_distance(p1: Coord, p2: Coord) -> float:
    distance: float = haversine(p1, p2, unit='m')
    return distance


def add_nodes(g: MetroGraph, stations_list: Stations, i: int) -> None:
    g.add_node(stations_list[i].id, info=stations_list[i],
               position=stations_list[i].position)
    g.add_node(stations_list[i + 1].id, info=stations_list[i + 1],
               position=stations_list[i + 1].position)


def add_edge(g: MetroGraph, node_a: int, node_b: int, edge_type: str,
             distance: float, col_id: str) -> None:
    edge = Edge(edge_type, distance, col_id)
    g.add_edge(node_a, node_b, info=edge)


def transbordaments(g: MetroGraph, stations_list: Stations) -> None:
    for stationA in stations_list:
        for stationB in stations_list:
            if stationA.name == stationB.name and stationA.id != stationB.id:
                distance: float = get_distance(stationA.position,
                                               stationB.position)
                col_id: str = stationA.color_line
                add_edge(g, stationA.id, stationB.id, "enllaç",
                         distance, col_id)


def add_stations_edges(g: MetroGraph) -> None:  # tipus, (linia), dist, color
    """Adds, as nodes, all stations to the graph and connects them with
       edges."""
    stations_list: Stations = read_stations()
    n: int = len(stations_list)
    for i in range(n - 1):
        add_nodes(g, stations_list, i)
        # We will add an edge between station i and station i + 1 if they share
        # the same line and are not the same station.
        if stations_list[i].line == stations_list[i + 1].line:
            distance: float = get_distance(stations_list[i].position,
                                           stations_list[i + 1].position)
            col_id: str = stations_list[i].color_line
            add_edge(g, stations_list[i].id, stations_list[i + 1].id, "tram",
                     distance, col_id)
    # We connect all nodes "station" that have the same name but different line
    # The edge type is "enllaç"
    transbordaments(g, stations_list)


def add_accesses_edges(g: MetroGraph) -> None:
    """Adds, as nodes, all accesses to the graph and connects them to their
       respective station."""
    accesses_list: Accesses = read_accesses()
    stations_list: Stations = read_stations()
    # Every access is added as a node and connected to its station node.
    # CONNECTO CADA ACCESS AMB TOTES LES ESTACIONS A LES QUE VA UNIDES
    for access in accesses_list:
        g.add_node(access.id, info=access, position=access.position)
        for station in stations_list:
            if access.station_name == station.name:
                distance: float = get_distance(access.position,
                                               station.position)
                add_edge(g, access.id, station.id, "access", distance,
                         "black")


def get_metro_graph() -> MetroGraph:
    """Returns a graph with stations and accesses as nodes."""
    g = nx.Graph()
    # First we add and connect the stations.
    add_stations_edges(g)
    # Then we add the access and connect them to their respective station.
    add_accesses_edges(g)
    return g


def show(g: MetroGraph) -> None:
    """Prints the representation of a graph with nodes painted in blue and
       edges in black"""
    # To place each node in the correct position we need the function
    # as "get_node_attributes()" that returns a dictionary with the nodes
    # labels elements and their position coordinates as values.
    pos = nx.get_node_attributes(g, 'position')
    nx.draw(g, pos, node_size=10)
    plt.show()


def plot(g: MetroGraph, filename: str) -> None:
    """Prints the representation of a graph on top of a map with nodes painted
       in black and edges in different colors, depending on the line they
       represent."""
    # We create the list edges which is a list of edges, each one represented
    # as a Tuple of two nodes.
    edges: List[Tuple[str, str]] = list(g.edges)
    # We create the dictionary pos that contains the position of every node in
    # the graph.
    pos = nx.get_node_attributes(g, 'position')
    # We create the empty map
    m = StaticMap(3000, 4000, 80)
    for i in range(len(edges)):
        # We get the position of the two nodes that connect the edge i
        posNodeA: Coord = (pos[edges[i][0]][0], pos[edges[i][0]][1])
        posNodeB: Coord = (pos[edges[i][1]][0], pos[edges[i][1]][1])
        # We add the two nodes to the map with the functin add_marker() as
        # black circles.
        m.add_marker(CircleMarker(posNodeA, "black", 6))
        m.add_marker(CircleMarker(posNodeB, "black", 6))
        # We get the color of the line that connects NodeA and NodeB getting
        # the attribute "col_id" of the edge i.
        col_id: str = g[edges[i][0]][edges[i][1]]["info"].col_id
        # We add the edge that connects NodeA and NodeB to the map.
        m.add_line(Line((posNodeA, posNodeB), col_id, 5))
    # We save the map.
    image = m.render(zoom=14)
    image.save(filename)

# def main():
#     g: MetroGraph = get_metro_graph()
#     print("Nodes", g.number_of_nodes())
#     print("Edges", g.number_of_edges())
#     show(g)
#     plot(g, 'metro.png')
#
# main()
