import json
import os
import heapq
from typing import List, Dict, Optional, Tuple, Set
from collections import deque

class NavigationService:
    def __init__(self):
        self.locations: Dict[str, Dict] = {}
        self.graph: Dict[str, List[str]] = {}
        self._load_layout()

    def _load_layout(self):
        # Determine the file path
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(current_dir, "data", "stadium_layout.json")
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                
            for loc in data["locations"]:
                self.locations[loc["id"]] = loc
                self.graph[loc["id"]] = loc.get("nearby_ids", [])
        except Exception as e:
            print(f"Error loading stadium layout JSON: {e}")
            # Fallback empty structures
            self.locations = {}
            self.graph = {}

    def get_location(self, loc_id: str) -> Optional[Dict]:
        return self.locations.get(loc_id)

    def fuzzy_match_location(self, query: str) -> Optional[Dict]:
        """Fuzzy match query text to find the intended location"""
        if not query:
            return None
        
        query = query.lower().strip()
        
        # Exact match of ID
        if query in self.locations:
            return self.locations[query]
            
        # Match by name
        for loc_id, loc in self.locations.items():
            if query in loc["name"].lower():
                return loc
            if query in loc.get("description", "").lower():
                return loc
                
        # Match by type
        # E.g., if user asks "washroom", find the closest washroom if starting location known.
        # We'll return the first match here, but we can do smarter routing in caller.
        for loc_id, loc in self.locations.items():
            if query in loc["type"].lower():
                return loc

        return None

    def find_nearest_facility(self, start_id: str, facility_type: str, crowd_data: Dict[str, int] = None) -> Optional[str]:
        """Find the nearest facility of a certain type using BFS (shortest path in terms of steps)"""
        if start_id not in self.locations:
            return None
            
        visited = {start_id}
        queue = deque([start_id])
        
        while queue:
            curr_id = queue.popleft()
            curr_loc = self.locations[curr_id]
            
            if curr_loc["type"] == facility_type:
                # If crowd_data is passed, check if the facility is in a critical zone.
                # If so, maybe keep searching for another one if available, but for now return this.
                return curr_id
                
            for neighbor in self.graph.get(curr_id, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    
        return None

    def get_directions(self, start_id: str, end_id: str, crowd_data: Dict[str, int] = None) -> List[Dict]:
        """
        Generate directions from start_id to end_id.
        Incorporates crowd density to route around congested zones if crowd_data is provided.
        Uses Dijkstra's algorithm.
        """
        if start_id not in self.locations or end_id not in self.locations:
            return []

        # Dijkstra algorithm
        # Priority queue stores (cost, current_node, path_taken)
        pq = [(0.0, start_id, [])]
        visited = {} # Stores min cost to reach node
        
        while pq:
            cost, curr, path = heapq.heappop(pq)
            
            if curr == end_id:
                full_path = path + [curr]
                return [self.locations[node_id] for node_id in full_path]
                
            if curr in visited and visited[curr] <= cost:
                continue
                
            visited[curr] = cost
            
            for neighbor in self.graph.get(curr, []):
                if neighbor not in self.locations:
                    continue
                
                # Base weight is 1.0 (each step is 1 segment)
                weight = 1.0
                
                # If crowd data is available, penalize paths going through crowded zones
                if crowd_data:
                    neighbor_loc = self.locations[neighbor]
                    zone = neighbor_loc["zone"]
                    density = crowd_data.get(zone, 0)
                    
                    if density > 90:
                        # Critical density - heavy penalty to try to route around
                        weight += 20.0
                    elif density > 75:
                        # High density - medium penalty
                        weight += 5.0
                    elif density > 50:
                        # Moderate density - light penalty
                        weight += 1.5
                
                new_cost = cost + weight
                heapq.heappush(pq, (new_cost, neighbor, path + [curr]))
                
        # If no path found (disconnected graph), fallback to standard BFS
        return []

    def format_directions_steps(self, path: List[Dict]) -> List[str]:
        """Convert a path list of locations into natural language step-by-step instructions"""
        if not path or len(path) < 2:
            return ["You are already at your destination."]
            
        instructions = []
        for i in range(len(path) - 1):
            curr = path[i]
            next_loc = path[i+1]
            
            # Level transition
            if curr["level"] != next_loc["level"]:
                action = "Take the escalator" if "esc" in next_loc["id"] or "esc" in curr["id"] else "Head"
                instructions.append(
                    f"{action} from {curr['name']} to Level {next_loc['level']} ({next_loc['name']})."
                )
            else:
                # Same level movement
                instructions.append(
                    f"From {curr['name']}, walk towards {next_loc['name']} in the {next_loc['zone']} zone."
                )
                
        instructions.append(f"You have arrived at {path[-1]['name']}.")
        return instructions

navigation_service = NavigationService()
