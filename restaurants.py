from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, TypeAlias
from fuzzysearch import find_near_matches
import pandas as pd # type: ignore
import requests
import io
import os
import pickle

Coord: TypeAlias = Tuple[float, float]

@dataclass
class Restaurant:
    name: str
    street: str
    secondary_filters: str
    position: Coord

Restaurants: TypeAlias = List[Restaurant]

def read() -> Restaurants:
    """Returns a list of all restaurants"""
    url = 'restaurants.csv'
    # Read the csv file and keep only few columns
    df = pd.read_csv(url, usecols=['name', 'addresses_road_name', 'secondary_filters_name', 'geo_epgs_4326_x', 'geo_epgs_4326_y'])
    restaurants_list: Restaurants = []
    for row in df.itertuples():
        r = Restaurant(row.name, row.addresses_road_name, row.secondary_filters_name, (row.geo_epgs_4326_y, row.geo_epgs_4326_x))
        restaurants_list.append(r)
    return restaurants_list

def find(query: str, restaurants: Restaurants) -> Restaurants:
    """Returns a list of all restaurants that contain the query in their description"""
    restaurants_list: Restaurants = []
    for restaurant in restaurants:
        elements: List[str] = [restaurant.name, restaurant.street, restaurant.secondary_filters]
        for attribute in elements:
            if type(attribute) == str:
                if query.lower() in attribute.lower():
                    restaurants_list.append(restaurant)
    return restaurants_list

def def_find(query: str, restaurants: Restaurants) -> Restaurants:
    """Returns a list of all restaurants that contain the query in their description"""
    restaurants_list: Restaurants = []
    for restaurant in restaurants:
        elements: List[str] = [restaurant.name, restaurant.street, restaurant.secondary_filters]
        for attribute in elements:
            if type(attribute) == str:
                if len(find_near_matches(query, attribute, max_l_dist=1)) != 0:
                    find: str = find_near_matches(query, attribute, max_l_dist=1)[0].matched
                    restaurants_list.append(restaurant)
    return restaurants_list

def save_restaurants_list(restaurants_list: Restaurants, filename: str) -> None:
    pickle_out = open(filename,"wb")
    pickle.dump(restaurants_list, pickle_out)
    pickle_out.close()

def load_restaurants(filename: str) -> Restaurants:
    if os.path.exists(filename):
        pickle_in = open(filename,"rb")
        restaurants_list: Restaurants = pickle.load(pickle_in)
        pickle_in.close()
    else:
        restaurants_list = read()
        save_restaurants_list(restaurants_list, filename)
    return restaurants_list
