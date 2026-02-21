from airport_coords import get_coords, load_airport_coords
import os

print("--- Testing Airport Coords ---")
load_airport_coords()

test_codes = ['KJFK', 'KLAX', 'CYYZ', 'EGLL']
for code in test_codes:
    lat, lon, found = get_coords(code)
    print(f"{code}: ({lat}, {lon}) [Found: {found}]")
