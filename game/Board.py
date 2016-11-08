import networkx
import enum
import random
from itertools import chain
from typing import List, Tuple

"""
Structure
---------
The board is represented as follows:
It consists of two parts:
a graph that represents the items around the hexagon, and an array of the hexagons.
The graph will hold the "shape":
 -each vertex will be a place a house can be built in
 -each edge will be a place a road can be paved at
THe array will hold the "data":
 -each item will be a hexagon, that consists of:
    --the element (Wheat, Metal, Clay or Wood)
    --the number (2-12)
    --Is there a burglar on the hexagon or not
each edge & vertex in the graph will be bi-directionally linked to it's hexagons, for easy traversal

Example
-------
This map (W2 means wool  with the number 5 on it, L2 is lumber with 2 on it):

    O     O
 /    \ /    \
O      O      O
| (W5) | (L2) |
O      O      O
 \    / \    /
    O     O

In the DS, will be represented as follows:
The array:
 ---- ----
| W5 | L2 |
 ---- ----
The graph will have the shape of the map, where the edges are \,/,|
and the vertices are O.
    O     O
 /    \ /    \
O      O      O
|      |      |
O      O      O
 \    / \    /
    O     O

"""


class Resource(enum.Enum):
    Brick = 1
    Lumber = 2
    Wool = 3
    Grain = 4
    Ore = 5
    Desert = 6


class Colony(enum.Enum):
    Settlement = 1
    City = 2
    Uncolonised = 3


class Road(enum.Enum):
    Road = 1
    Unpaved = 2


Location = int
"""Location is a vertex in the graph
A place that can be colonised (with a settlement, and later with a city)
"""

Path = Tuple[int, int]
"""Path is an edge in the graph
A place that a road can be paved in
"""

Land = Tuple[Resource, int]
"""Land is an element in the lands array
A hexagon in the catan map, that has a resource type and a number between [2,12]
"""


class Board:
    _player = 'player'
    _lands = 'lands'

    def __init__(self):
        self._shuffle_map()
        self._create_graph()

    def get_all_settleable_locations(self) -> List[Location]:
        """get non-colonised (empty vertices) locations on map"""
        return [v for v in self._roads_and_colonies.nodes()
                if not self.is_colonised(v)]

    def get_settleable_locations_by_player(self, player) -> List[Location]:
        """get non-colonised (empty vertices) locations on map that this player can settle"""
        non_colonised = [v for v in self._roads_and_colonies.nodes_iter()
                         if not self.is_colonised(v)]
        coloniseable = []
        for u in non_colonised:
            is_coloniseable = True
            one_hop_from_non_colonised = []
            for v in self._roads_and_colonies.neighbors(u):
                if self.is_colonised(v):
                    is_coloniseable = False
                    break
                if self.has_road_been_paved_by(player, (u, v)):
                    one_hop_from_non_colonised.append(v)
            if not is_coloniseable:
                continue

            is_coloniseable = False
            for v in one_hop_from_non_colonised:
                for w in self._roads_and_colonies.neighbors(v):
                    if w != u and self.has_road_been_paved_by(player, (v, w)):
                        is_coloniseable = True
                        break
            if is_coloniseable:
                coloniseable.append(u)
        return coloniseable

    def get_unpaved_roads_near_player(self, player) -> List[Path]:
        """get unpaved (empty edges) paths on map that this player can pave"""
        roads = [e for e in self._roads_and_colonies.edges_iter()
                 if self.has_road_been_paved_by(player, e)]
        locations_non_colonised_by_other_players = [
            v for v in set(chain(*roads))
            if self._roads_and_colonies.node[v]['player'][0] in [player, None]]
        return [(u, v) for u in locations_non_colonised_by_other_players
                for v in self._roads_and_colonies.neighbors(u)
                if self._roads_and_colonies[u][v]['player'][0] is None]

    def get_settled_locations_by_player(self, player) -> List[Location]:
        return [v for v in self._roads_and_colonies.nodes()
                if self._roads_and_colonies.node[v]['player'][0] == player]

    def get_surrounding_resources(self, location: Location) -> List[Land]:
        """get resources surrounding the settlement in this location"""
        return self._roads_and_colonies.node[location]['lands']

    def settle_location(self, player, location: Location, colony: Colony):
        self._roads_and_colonies.node[location]['player'] = (player, colony)

    def pave_road(self, player, location: Path):
        self._roads_and_colonies[location[0]][location[1]]['player'] = (player, Road.Road)

    def is_colonised(self, v):
        return self._roads_and_colonies.node[v]['player'][0] is not None

    def has_road_been_paved_by(self, player, path: Path):
        """returns True if road (in the given path) was paved by given player,
        returns False otherwise"""
        return self._roads_and_colonies[path[0]][path[1]]['player'][0] == player

    _vertices_rows = [
        [i for i in range(0, 3)],
        [i for i in range(3, 7)],
        [i for i in range(7, 11)],
        [i for i in range(11, 16)],
        [i for i in range(16, 21)],
        [i for i in range(21, 27)],
        [i for i in range(27, 33)],
        [i for i in range(33, 38)],
        [i for i in range(38, 43)],
        [i for i in range(43, 47)],
        [i for i in range(47, 51)],
        [i for i in range(51, 54)]
    ]
    _vertices = [v for vertices_row in _vertices_rows for v in vertices_row]

    def _shuffle_map(self):
        land_numbers = [2, 12] + [i for i in range(3, 12) if i != 7] * 2
        land_resources = [Resource.Lumber, Resource.Wool, Resource.Grain] * 4 + \
                         [Resource.Brick, Resource.Ore] * 3

        random.shuffle(land_numbers)
        random.shuffle(land_resources)

        land_resources.append(Resource.Desert)
        land_numbers.append(0)

        lands = zip(land_resources, land_numbers, range(len(land_resources)))
        self._lands = [land for land in lands]

    def _create_graph(self):
        self._roads_and_colonies = networkx.Graph()
        self._roads_and_colonies.add_nodes_from(Board._vertices)
        self._roads_and_colonies.add_edges_from(Board._create_edges())
        self._set_attributes()

    @staticmethod
    def _create_edges():
        edges = []
        for i in range(5):
            Board._create_row_edges(edges, i, i + 1, Board._vertices_rows, i % 2 == 0)
            Board._create_row_edges(edges, -i - 1, -i - 2, Board._vertices_rows, i % 2 == 0)
        Board._create_odd_rows_edges(edges, Board._vertices_rows[5], Board._vertices_rows[6])
        return edges

    @staticmethod
    def _create_row_edges(edges, i, j, vertices_rows, is_even_row):
        if is_even_row:
            Board._create_even_rows_edges(edges, vertices_rows[j], vertices_rows[i])
        else:
            Board._create_odd_rows_edges(edges, vertices_rows[j], vertices_rows[i])

    @staticmethod
    def _create_odd_rows_edges(edges, first_row, second_row):
        for edge in zip(second_row, first_row):
            edges.append(edge)

    @staticmethod
    def _create_even_rows_edges(edges, larger_row, smaller_row):
        for i in range(len(smaller_row)):
            edges.append((smaller_row[i], larger_row[i]))
            edges.append((smaller_row[i], larger_row[i + 1]))

    def _set_attributes(self):
        vertices_to_lands = self._create_vertices_to_lands_mapping()
        self._set_vertices_attributes(vertices_to_lands)
        self._set_edges_attributes(vertices_to_lands)

    def _set_vertices_attributes(self, vertices_to_lands):
        networkx.set_node_attributes(self._roads_and_colonies, 'lands', vertices_to_lands)
        vertices_to_players = {v: (None, Colony.Uncolonised) for v in Board._vertices}
        networkx.set_node_attributes(self._roads_and_colonies, 'player', vertices_to_players)

    def _set_edges_attributes(self, vertices_to_lands):
        for edge in self._roads_and_colonies.edges_iter():
            lands_intersection = [land for land in vertices_to_lands[edge[0]]
                                  if land in vertices_to_lands[edge[1]]]
            edge_attributes = self._roads_and_colonies[edge[0]][edge[1]]
            edge_attributes['lands'] = lands_intersection
            edge_attributes['player'] = (None, Road.Unpaved)

    def _create_vertices_to_lands_mapping(self):
        land_rows = [
            self._lands[0:3],
            self._lands[3:7],
            self._lands[7:12],
            self._lands[12:16],
            self._lands[16:19]
        ]
        vertices_rows_per_land_row = [
            Board._vertices_rows[0:3] + [Board._vertices_rows[3][1:-1]],
            Board._vertices_rows[2:5] + [Board._vertices_rows[5][1:-1]],
            Board._vertices_rows[4:8],
            [Board._vertices_rows[6][1:-1]] + Board._vertices_rows[7:10],
            [Board._vertices_rows[8][1:-1]] + Board._vertices_rows[9:12]
        ]
        vertices_map = {vertex: [] for vertex in Board._vertices}
        for vertices_rows, land_row in zip(vertices_rows_per_land_row, land_rows):
            Board._create_top_vertex_mapping(vertices_map, vertices_rows[0], land_row)
            Board._create_middle_vertex_mapping(vertices_map, vertices_rows[1], land_row)
            Board._create_middle_vertex_mapping(vertices_map, vertices_rows[2], land_row)
            Board._create_top_vertex_mapping(vertices_map, vertices_rows[3], land_row)
        return vertices_map

    @staticmethod
    def _create_top_vertex_mapping(vertices_map, vertices, lands):
        for vertex, land in zip(vertices, lands):
            vertices_map[vertex].append(land)

    @staticmethod
    def _create_middle_vertex_mapping(vertices_map, vertices, lands):
        vertices_map[vertices[0]].append(lands[0])
        vertices_map[vertices[-1]].append(lands[-1])

        for i in range(1, len(vertices[1:-1]) + 1):
            vertices_map[vertices[i]].append(lands[i - 1])
            vertices_map[vertices[i]].append(lands[i])