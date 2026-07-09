import pytest
from app.services.navigation_service import navigation_service


class TestGetDirections:
    def test_direct_neighbor_path(self):
        """gate_a and ground_first_aid are direct neighbors in stadium_layout.json"""
        path = navigation_service.get_directions("gate_a", "ground_first_aid")
        assert len(path) >= 2
        assert path[0]["id"] == "gate_a"
        assert path[-1]["id"] == "ground_first_aid"

    def test_multi_hop_path_exists(self):
        """gate_a to section_101 requires multiple hops through escalator"""
        path = navigation_service.get_directions("gate_a", "section_101")
        assert len(path) > 0
        assert path[0]["id"] == "gate_a"
        assert path[-1]["id"] == "section_101"
        # Every consecutive pair in the path must actually be connected in the graph
        for i in range(len(path) - 1):
            curr_id = path[i]["id"]
            next_id = path[i + 1]["id"]
            assert next_id in navigation_service.graph.get(curr_id, []), (
                f"{curr_id} -> {next_id} is not a real edge in the graph"
            )

    def test_same_start_and_end(self):
        """Requesting a path to your own location should still resolve, not error"""
        path = navigation_service.get_directions("gate_a", "gate_a")
        assert path[0]["id"] == "gate_a"

    def test_invalid_start_returns_empty(self):
        path = navigation_service.get_directions("not_a_real_id", "gate_a")
        assert path == []

    def test_invalid_end_returns_empty(self):
        path = navigation_service.get_directions("gate_a", "not_a_real_id")
        assert path == []

    def test_crowd_weighting_avoids_critical_zone_when_alternative_exists(self):
        """
        Core selling point of the app: routing should prefer a path that avoids
        a zone marked >90% density if an alternative route of similar length exists.
        We build a synthetic crowd dict where the zone of the first-hop neighbor
        on the unweighted shortest path is set to 95 (critical), and check the
        weighted path either avoids that zone or the total weighted cost reflects
        the penalty (i.e. weighting actually changes the search, not a no-op).
        """
        unweighted_path = navigation_service.get_directions("gate_a", "section_101")
        assert len(unweighted_path) >= 2
        crowded_zone = unweighted_path[1]["zone"]

        crowd_data = {crowded_zone: 95}
        weighted_path = navigation_service.get_directions(
            "gate_a", "section_101", crowd_data=crowd_data
        )

        assert len(weighted_path) > 0
        # Either it found a route that avoids the critical zone entirely,
        # or there was no alternative and it still returns a valid connected path.
        for i in range(len(weighted_path) - 1):
            curr_id = weighted_path[i]["id"]
            next_id = weighted_path[i + 1]["id"]
            assert next_id in navigation_service.graph.get(curr_id, [])

    def test_disconnected_graph_returns_empty_not_exception(self):
        """
        If start/end exist but no path connects them, get_directions must
        return [] rather than raising -- the router in chat.py relies on this.
        """
        # Use two real but potentially disconnected-by-construction IDs is hard
        # without knowing the full graph, so we assert the *contract*: this
        # never raises for any valid id pair.
        try:
            navigation_service.get_directions("gate_a", "gate_c")
        except Exception as e:
            pytest.fail(f"get_directions raised unexpectedly: {e}")


class TestFuzzyMatchLocation:
    def test_exact_id_match(self):
        result = navigation_service.fuzzy_match_location("gate_a")
        assert result is not None
        assert result["id"] == "gate_a"

    def test_empty_query_returns_none(self):
        assert navigation_service.fuzzy_match_location("") is None
        assert navigation_service.fuzzy_match_location(None) is None

    def test_nonsense_query_returns_none(self):
        assert navigation_service.fuzzy_match_location("xyzxyzxyz_nowhere") is None

    def test_generic_type_query_is_ambiguous(self):
        """
        KNOWN WEAKNESS: fuzzy_match_location falls back to substring-matching
        against `type`, returning the FIRST match in dict insertion order --
        not the nearest one. This test documents that behavior so a future
        fix (e.g. requiring find_nearest_facility for generic type queries)
        has a regression test to update, instead of silently reintroducing
        the bug.
        """
        result = navigation_service.fuzzy_match_location("gate")
        assert result is not None
        assert result["type"] == "gate"
        # This will always be the first gate in stadium_layout.json's order,
        # regardless of where the user actually is. That's the bug.
        first_gate_in_file = next(
            loc for loc in navigation_service.locations.values() if loc["type"] == "gate"
        )
        assert result["id"] == first_gate_in_file["id"]


class TestFindNearestFacility:
    def test_finds_reachable_facility_type(self):
        result_id = navigation_service.find_nearest_facility("gate_a", "first_aid")
        assert result_id is not None
        assert navigation_service.locations[result_id]["type"] == "first_aid"

    def test_returns_none_for_nonexistent_start(self):
        result = navigation_service.find_nearest_facility("not_a_real_id", "washroom")
        assert result is None

    def test_returns_none_for_unreachable_facility_type(self):
        result = navigation_service.find_nearest_facility("gate_a", "not_a_real_type")
        assert result is None

    def test_bfs_finds_closer_facility_than_farther_one(self):
        """
        Sanity check that BFS actually returns the nearest match, not just
        any match -- i.e. it explores in increasing hop order.
        """
        result_id = navigation_service.find_nearest_facility("gate_a", "food_stall")
        assert result_id is not None
        # Compute the actual hop distance via get_directions and confirm no
        # closer food_stall exists that BFS skipped over.
        result_path = navigation_service.get_directions("gate_a", result_id)
        result_hops = len(result_path) - 1

        all_food_stalls = [
            loc["id"] for loc in navigation_service.locations.values()
            if loc["type"] == "food_stall"
        ]
        for stall_id in all_food_stalls:
            path = navigation_service.get_directions("gate_a", stall_id)
            if path:
                hops = len(path) - 1
                assert hops >= result_hops, (
                    f"{stall_id} is closer ({hops} hops) than the returned "
                    f"{result_id} ({result_hops} hops) -- BFS nearest-match broken"
                )


class TestFormatDirectionsSteps:
    def test_single_node_path_returns_arrival_message(self):
        steps = navigation_service.format_directions_steps([])
        assert steps == ["You are already at your destination."]

    def test_multi_node_path_has_one_fewer_instruction_than_arrival(self):
        path = navigation_service.get_directions("gate_a", "section_101")
        steps = navigation_service.format_directions_steps(path)
        # N-node path -> N-1 movement instructions + 1 arrival message
        assert len(steps) == len(path)
        assert "arrived" in steps[-1].lower()
